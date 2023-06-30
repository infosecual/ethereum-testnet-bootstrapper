"""
ConsensusMonitors provide a generic interface that allows you to
create and run various metrics.

The metric defines:
    - measure_metric: A method that given a client, takes a measurement.
    - collect_metrics: Defines how to collect the measurements from the clients.
    - report_metric: Creates a report for the metric.
"""
import asyncio
from abc import abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Union, Any, Callable, Optional
import logging

import requests

from ...config.etb_config import ClientInstance
from ...interfaces.client_request import ClientInstanceRequest, perform_batched_request, BeaconAPIgetBlockV2, \
    BeaconAPIgetFinalityCheckpoints

"""
Consensus Monitors are meant to be standalone actions that can be performed
by a testnet_monitor or any other module.
"""
# clients grouped by result, unreachable_clients, invalid_response_clients
ConsensusMonitorResult = tuple[dict[Any, list[ClientInstance]], list[ClientInstance], list[ClientInstance]]


class ClientInstanceMonitor:
    """
        A monitor that can be run on a testnet.

        Provides a small interface to perform a query async on a client.

        A client query should:
            return an exception if we couldn't get a response from the client.
            return Any if got a response from the client.

        A response_parser should given the response of the query:
            return the parsed result.
            return None if the response is invalid.


        A report_metric routine is implemented by the user to report the metric.
    """

    def __init__(self,
                 client_query: Callable[[ClientInstance], Union[Exception, Any]],
                 response_parser: Callable[[Any], Optional[Any]],
                 max_retries_for_consensus: int = 0,
                 ):

        self.client_query = client_query
        self.response_parser = response_parser

        self.max_retries_for_consensus = max_retries_for_consensus

    def _query_clients_for_result(self, clients_to_monitor: list[ClientInstance]) -> ConsensusMonitorResult:
        client_futures = {}
        with ThreadPoolExecutor(max_workers=len(clients_to_monitor)) as executor:
            for client in clients_to_monitor:
                client_futures[client] = executor.submit(self.client_query, client)

        # iterate through the futures and group them by result, unreachable, invalid_response
        results: dict[Any, list[ClientInstance]] = {}
        unreachable_clients = []
        invalid_response_clients = []
        for client, future in client_futures.items():
            result = future.result()
            # connection error
            if isinstance(result, Exception):
                unreachable_clients.append(client)
                continue

            parsed_result = self.response_parser(result)
            # parsing error
            if parsed_result is None:
                invalid_response_clients.append(client)
                continue
            # good response
            if parsed_result not in results:
                results[parsed_result] = []
            results[parsed_result].append(client)

        return results, unreachable_clients, invalid_response_clients

    def query_clients_for_metric(self, clients_to_monitor: list[ClientInstance]) -> ConsensusMonitorResult:
        """
        Query the clients for the result.
        """
        results = self._query_clients_for_result(clients_to_monitor)
        for _ in range(self.max_retries_for_consensus):
            if len(results[0]) == 1:
                return results
            results = self._query_clients_for_result(clients_to_monitor)
        return results

    def report_metric(self, results: ConsensusMonitorResult) -> str:
        """Report the results obtained from the measurements."""
        out = ''
        for result, clients in results[0].items():
            out += f"{result}: {[client.name for client in clients]}\n"
        if len(results[1]) > 0:
            out += f"Unreachable Clients: {[client.name for client in results[1]]}\n"
        if len(results[2]) > 0:
            out += f"Invalid Response Clients: {[client.name for client in results[2]]}\n"
        return out

    def run(self, clients_to_monitor: list[ClientInstance]) -> str:
        """Run the monitor."""
        results = self.query_clients_for_metric(clients_to_monitor)
        return self.report_metric(results)


ClientHead = tuple[int, str, str]


class HeadsMonitor(ClientInstanceMonitor):
    """
        A monitor that reports the heads of the clients.
        It will retry the query up to max_retries_for_consensus times.
    """

    def __init__(self, max_retries: int = 3, timeout: int = 5,
                 max_retries_for_consensus: int = 3):
        self.query = BeaconAPIgetBlockV2(max_retries=max_retries, timeout=timeout)
        self.max_retry_for_consensus = max_retries_for_consensus

        super().__init__(client_query=self.query.perform_request,
                         response_parser=self._get_client_head_from_block)

    def _get_client_head_from_block(self, response: requests.Response) -> Optional[ClientHead]:
        try:
            block = self.query.get_block(response)
            slot = block["slot"]
            state_root = f'0x{block["state_root"][-8:]}'
            graffiti = (
                bytes.fromhex(block["body"]["graffiti"][2:])
                .decode("utf-8")
                .replace("\x00", "")
            )
            return slot, state_root, graffiti
        except Exception as e:
            logging.debug(f"Exception parsing response: {e}")
            return None

    def report_metric(self, results: ConsensusMonitorResult) -> str:
        """Report the results obtained from the measurements."""
        out = f"num_forks: {len(results[0]) - 1}\n"
        for head, clients in results[0].items():
            out += f"({head}) : {[client.name for client in clients]}\n"
        if len(results[1]) > 0:
            out += f"Unreachable Clients: {[client.name for client in results[1]]}\n"
        if len(results[2]) > 0:
            out += f"Invalid Response Clients: {[client.name for client in results[2]]}\n"
        return out


# (epoch, root)
Checkpoint = tuple[int, str]
# finalized, justified, previous_justified
Checkpoints = tuple[Checkpoint, Checkpoint, Checkpoint]


class CheckpointsMonitor(ClientInstanceMonitor):
    def __init__(self, max_retries: int = 3, timeout: int = 5,
                 max_retries_for_consensus: int = 3):
        self.query = BeaconAPIgetFinalityCheckpoints(max_retries=max_retries, timeout=timeout)
        self.max_retry_for_consensus = max_retries_for_consensus

        super().__init__(client_query=self.query.perform_request,
                         response_parser=self._get_checkpoints)

    def _get_checkpoints(self, response: requests.Response) -> Optional[str]:
        try:
            # checkpoints
            finalized_cp: tuple[int, str]
            current_justified_cp: tuple[int, str]
            previous_justified_cp: tuple[int, str]

            finalized_cp = self.query.get_finalized_checkpoint(response)
            fc_epoch = finalized_cp[0]
            fc_root = f"0x{finalized_cp[1][-8:]}"
            fc = (fc_epoch, fc_root)

            current_justified_cp = self.query.get_current_justified_checkpoint(
                response
            )
            cj_epoch = current_justified_cp[0]
            cj_root = f"0x{current_justified_cp[1][-8:]}"
            cj = (cj_epoch, cj_root)

            previous_justified_cp = self.query.get_previous_justified_checkpoint(
                response
            )
            pj_epoch = previous_justified_cp[0]
            pj_root = f"0x{previous_justified_cp[1][-8:]}"
            pj = (pj_epoch, pj_root)

            return f"finalized: {fc}, current justified: {cj}, previous justified: {pj}"

        except Exception as e:
            logging.debug(f"Exception parsing response: {e}")
            return None
