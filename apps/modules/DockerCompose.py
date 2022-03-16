import re

from ruamel import yaml

# TODO: use this to clean up client writers.


class ConfigurationEnvironment(object):
    """
    Crawler that goes through all of the configurations of a module
    and grabs the required variables.
    """

    def __init__(self, client_writer):
        self.cw = client_writer
        self.gc = self.cw.gc
        self.cc = self.cw.cc
        self.ecc = None
        self.ccc = None
        # configs
        self.ecc = self.cw.ecc
        self.ccc = self.cw.ccc
        self.ebc = self.cw.ebc
        self.cbc = self.cw.cbc

        print(f"{self.cc} \n{self.ecc}\n{self.ccc}\n{self.ebc}\n{self.cbc}")
        # if "consensus-config" in self.cc:
        #     self.ccc = self.gc["consensus-configs"][self.cc["consensus-config"]]
        # if "execution-config" in self.cc:
        #     self.ecc = self.gc["execution-configs"][self.cc["execution-config"]]
        # elif "execution-config" in self.ccc:  # cl client with el client
        #     self.ecc = self.gc["execution-configs"][self.ccc["execution-config"]]

        self.variable_getters = {
            # generic
            "start-ip-addr": self.get_ip,
            "netrestrict-range": self.get_ip_subnet,
            # execution
            "execution-data-dir": self.get_execution_data_dir,
            "execution-p2p-port": self.get_static_port,
            "execution-http-port": self.get_static_port,
            "execution-ws-port": self.get_static_port,
            "http-apis": self.get_execution_config,
            "ws-apis": self.get_execution_config,
            "chain-id": self.get_execution_config,
            "network-id": self.get_execution_config,
            "execution-genesis": self.get_execution_genesis,
            "terminaltotaldifficulty": self.get_ttd,
            # consensus
            "preset-base": self.get_consensus_preset,
            "start-fork": self.get_genesis_fork,
            "end-fork": self.get_end_fork,
            "testnet-dir": self.get_client_config,
            "node-dir": self.get_node_dir,
            "start-consensus-p2p-port": self.get_port,
            "start-beacon-api-port": self.get_port,
            "start-beacon-metric-port": self.get_port,
            "start-beacon-rpc-port": self.get_port,
            "start-validator-rpc-port": self.get_port,
            "start-validator-metric-port": self.get_port,
            "graffiti": self.get_graffiti,
            "execution-launcher": self.get_execution_launcher,
            "local-execution-client": self.get_consensus_config,
            "http-web3-ip-addr": self.get_consensus_config,
            "ws-web3-ip-addr": self.get_consensus_config,
            "consensus-target-peers": self.get_target_peers,
            # bootnodes
            "execution-bootnode-start-ip-addr": self.get_eb_ip_addr,
            "execution-bootnode-enode": self.get_eb_enode,
            "execution-bootnode-disc-port": self.get_eb_disc_port,
            "execution-bootnode-private-key": self.get_eb_private_key,
            "execution-bootnode-enode-file": self.get_eb_enode_file,
            "execution-bootnode-enode-dir": self.get_eb_enode_dir,
            "execution-bootnode-verbosity": self.get_eb_verbosity,
            "consensus-bootnode-start-ip-addr": self.get_cb_ip_addr,
            "consensus-bootnode-private-key": self.get_cb_private_key,
            "consensus-bootnode-enr-port": self.get_cb_enr_port,
            "consensus-bootnode-api-port": self.get_cb_api_port,  # should drop when we add more bootnodes
            "consensus-bootnode-enr-file": self.get_cb_enr_file,
        }

        # how to fetch various ports.
        self.port_maps = {}

    def get_environment_var(self, var):
        if var not in self.variable_getters:
            raise Exception(f"Tried to fetch unimplemented var: {var}.")
        else:
            getter = self.variable_getters[var]
            value = getter(var)
            if getter == self.get_static_port:
                p = re.compile(r"(?P<port>([A-Za-z0-9\-]+-port))")
                m = p.search(var)
                if m is None:
                    raise Exception(f"Unexpected port: {var}")
                variable = m.group("port")
            elif getter == self.get_port:
                p = re.compile(r"start-(?P<port>([A-Za-z0-9\-]+-port))")
                m = p.search(var)
                if m is None:
                    raise Exception(f"Unexpected port: {var}")
                variable = m.group("port")
            elif getter == self.get_ip:
                variable = "ip-addr"
            else:
                variable = var

            return f'{variable.upper().replace("-","_")}={value}'

    # Bootnodes
    # TODO: implement me for more situations
    def get_eb_ip_addr(self, unused):
        return self.ebc["execution-bootnode-start-ip-addr"]

    def get_eb_verbosity(self, unused):
        return self.ebc["execution-bootnode-verbosity"]

    def get_eb_enode(self, unused):
        return self.ebc["execution-bootnode-enode"]

    def get_eb_disc_port(self, unused):
        return self.ebc["execution-bootnode-disc-port"]

    def get_eb_private_key(self, unused):
        return self.ebc["execution-bootnode-private-key"]

    def get_eb_enode_file(self, unused):
        return self.ebc["execution-bootnode-enode-file"]

    def get_eb_enode_dir(self, unused):
        return self.ebc["execution-bootnode-enode-dir"]

    def get_cb_ip_addr(self, unused):
        return self.cbc["consensus-bootnode-start-ip-addr"]

    def get_cb_private_key(self, unused):
        return self.cbc["consensus-bootnode-private-key"]

    def get_cb_enr_port(self, unused):
        return self.cbc["consensus-bootnode-enr-port"]

    def get_cb_api_port(self, unused):
        return self.cbc["consensus-bootnode-api-port"]

    def get_cb_enr_file(self, unused):
        return self.cbc["consensus-bootnode-enr-file"]

    # Generic
    def get_client_config(self, var):
        return self.cc[var]

    def get_execution_config(self, var):
        return self.ecc[var]

    def get_consensus_config(self, var):
        return self.ccc[var]

    def get_ip(self, _unused="unused"):
        prefix = ".".join(self.cc["start-ip-addr"].split(".")[:3]) + "."
        base = int(self.cc["start-ip-addr"].split(".")[-1])
        ip = prefix + str(base + self.cw.curr_node)
        return ip

    def get_static_port(self, goal_port):
        return self.get_port(goal_port, static=True)

    def get_port(self, goal_port, static=False):
        if goal_port in self.cc:
            if static:
                return int(self.cc[goal_port])
            return str(int(self.cc[goal_port]) + self.cw.curr_node)
        elif self.ccc is not None and goal_port in self.ccc:
            if static:
                return int(self.ccc[goal_port])
            return str(int(self.ccc[goal_port]) + self.cw.curr_node)
        elif self.ecc is not None and goal_port in self.ecc:
            if static:
                return int(self.ecc[goal_port])
            return str(int(self.ecc[goal_port]) + self.cw.curr_node)
        else:
            raise Exception(f"Can't find a reference to {goal_port}")

    # Global Config
    def get_ttd(self, _unused="unused"):
        return self.gc["config-params"]["execution-layer"]["genesis-config"][
            "terminalTotalDifficulty"
        ]

    def get_execution_genesis(self, _unused="unused"):
        # TODO: generic
        return self.gc["files"]["geth-genesis"]

    def get_ip_subnet(self, _unused="unused"):
        return str(self.gc["docker"]["ip-subnet"])

    def get_consensus_preset(self, _unused="unused"):
        # used for setting correct launcher params.
        return str(self.gc["config-params"]["consensus-layer"]["preset-base"])

    def get_genesis_fork(self, _unused="unused"):
        # used for setting correct launcher params.
        return str(
            self.gc["config-params"]["consensus-layer"]["forks"]["genesis-fork-name"]
        )

    def get_end_fork(self, _unused="unused"):
        # used for setting correct launcher params.
        return str(
            self.gc["config-params"]["consensus-layer"]["forks"]["end-fork-name"]
        )

    # Client Config

    # Execution Config
    def get_execution_client_name(self, _unused="unused"):
        return self.ecc["client"]

    def get_execution_data_dir(self, _unused="unused"):
        if self.ccc is not None:
            return f"{self.get_node_dir()}/{self.get_execution_client_name()}"
        return self.cc["data-dir"]

    # Consensus Config
    def get_execution_launcher(self, _unused="unused"):
        if self.ccc["local-execution-client"]:
            return str(self.ccc["execution-launcher"])
        else:
            return None

    def get_graffiti(self, _unused="unused"):
        if "graffiti" in self.cc:
            return str(self.cc["graffiti"] + str(self.cw.curr_node))
        else:
            return str(self.cc["client-name"] + str(self.cw.curr_node))

    def get_node_dir(self, _unused="unused"):
        return f"{self.cc['testnet-dir']}/node_{self.cw.curr_node}"

    def get_target_peers(self, _unused="unused"):
        # count the number of consensus nodes in the network and subtract 1
        total_nodes = 0
        for cc in self.gc["consensus-clients"]:
            ccc = self.gc["consensus-configs"][
                self.gc["consensus-clients"][cc]["consensus-config"]
            ]
            total_nodes += ccc["num-nodes"]
        return total_nodes - 1


class ClientWriter(object):
    """
    Generic client class to write services to docker-compose
    Just use this template and add your entrypoint in child class.
    """

    def __init__(self, global_config, client_config, curr_node, use_root=False):
        self.use_root = use_root
        self.gc = global_config
        self.cc = client_config
        # used when we have multiple of the same client.
        self.curr_node = curr_node
        # constants.
        if "client-name" in self.cc:
            self.name = f"{self.cc['client-name']}-node-{curr_node}"
        else:
            self.name = f"{self.cc['container-name']}-node-{curr_node}"
        self.image = self.cc["image"]
        self.tag = self.cc["tag"]
        self.network_name = self.gc["docker"]["network-name"]
        self.volumes = [str(x) for x in self.gc["docker"]["volumes"]]

        # setup the configs for various modules needed by this client
        self._setup_configs()

        self.env = []

        # get number of consensus nodes
        self.num_consensus_nodes = 0
        for client in self.gc["consensus-clients"]:
            config = self.gc["consensus-clients"][client]
            ccc = self.gc["consensus-configs"][config["consensus-config"]]
            self.num_consensus_nodes += ccc["num-nodes"]

        self.base_consensus_env_vars = [
            "preset-base",
            "start-fork",
            "end-fork",
            "testnet-dir",
            "node-dir",
            "start-ip-addr",
            "start-consensus-p2p-port",
            "start-beacon-api-port",
            "graffiti",
            "netrestrict-range",
            "start-beacon-metric-port",
            "start-beacon-rpc-port",
            "start-validator-rpc-port",
            "start-validator-metric-port",
            "execution-launcher",
            "local-execution-client",
            "consensus-target-peers",
        ]
        self.consensus_with_execution_env_vars = [
            "http-web3-ip-addr",
            "ws-web3-ip-addr",
        ]
        self.base_execution_env_vars = [
            "start-ip-addr",
            "execution-data-dir",
            "execution-p2p-port",
            "execution-http-port",
            "execution-ws-port",
            "netrestrict-range",
            "http-apis",
            "ws-apis",
            "chain-id",
            "network-id",
            "execution-genesis",
            "terminaltotaldifficulty",
        ]
        self.base_execution_bootnode_env_vars = [
            "netrestrict-range",
            "execution-bootnode-start-ip-addr",
            "execution-bootnode-enode",
            "execution-bootnode-disc-port",
            "execution-bootnode-private-key",
            "execution-bootnode-enode-file",
            "execution-bootnode-enode-dir",
            "execution-bootnode-verbosity",
        ]
        self.base_consensus_bootnode_env_vars = [
            "consensus-bootnode-start-ip-addr",
            "consensus-bootnode-private-key",
            "consensus-bootnode-enr-port",
            "consensus-bootnode-api-port",  # should drop when we add more bootnodes
            "consensus-bootnode-enr-file",
        ]

    def _setup_configs(self):
        """
        Modules for various clients can include multiple configs and
        sometimes require some information for those.

        consensus-client:
            1. consensus-config (for its beacon and validator args)
            2. consensus-bootnode (bootnode to point the beacon node at)
            also inherits from the execution client if it is running one.

        execution-client:
            1. execution-config (for the local execution client if it has one)
            2. execution-bootnode (bootnode to point the execution client at)

        consensus-bootnode:
            1. consensus-bootnode

        execution-bootnode:
            1. execution-bootnode

        a consensus client has one config: consensus-config
            if local execution node the consensus-config has the config.
            consensus-bootnode contained in consensus-config
            execution-bootnode contained in execution-config

        a execution client has one config: exeuction-config
            execution bootnode contained in that config

        a consensus bootnode has one config: consensus-bootnode-config
        an execution bootnode has on config: execution-bootnode-config
        """
        self.ecc = None  # execution client config
        self.ccc = None  # consensus client config
        self.ebc = None  # execution bootnode config
        self.cbc = None  # consensus bootnode config

        print(f"Setting up configs for {self.name}: {self.cc}")
        # Consensus client check:
        if "consensus-config" in self.cc:
            self.ccc = self.gc["consensus-configs"][self.cc["consensus-config"]]

            self.cbc = self.gc["consensus-bootnode-configs"][
                self.ccc["consensus-bootnode-config"]
            ]
            # if there is also a local execution client
            if self.ccc["local-execution-client"]:
                self.ecc = self.gc["execution-configs"][self.ccc["execution-config"]]
                print(self.ecc)
            self.ebc = self.gc["execution-bootnode-configs"][
                self.ecc["execution-bootnode-config"]
            ]
            return

        # Execution client check
        if "execution-config" in self.cc:
            self.ecc = self.gc["execution-configs"][self.cc["execution-config"]]
            self.ebc = self.gc["execution-bootnode-configs"][
                self.ecc["execution-bootnode-config"]
            ]
            return

        # consensus bootnode check
        if "consensus-bootnode-config" in self.cc:
            self.cbc = self.gc["consensus-bootnode-configs"][
                self.cc["consensus-bootnode-config"]
            ]
            return

        if "execution-bootnode-config" in self.cc:
            self.ebc = self.gc["execution-bootnode-configs"][
                self.cc["execution-bootnode-config"]
            ]
            return

    def _environment(self):
        """
        Modules use environmental variables to define how to launch themselves.
        """
        environment = []
        # base case.
        if (
            self.ecc is None
            and self.ccc is None
            and "additional-env" not in self.cc
            and self.ebc is None
            and self.cbc is None
        ):
            return environment

        print(f"environment setup for: {self.cc}")
        config_env = ConfigurationEnvironment(self)
        # consensus client env vars
        if self.ccc is not None:
            print("adding consensus environment")
            for bcev in self.base_consensus_env_vars:
                environment.append(config_env.get_environment_var(bcev))
        # execution client env vars
        if self.ecc is not None:
            print("adding execution environment")
            for beev in self.base_execution_env_vars:
                environment.append(config_env.get_environment_var(beev))
            # go ahead and add the end fork just in case
            environment.append(config_env.get_environment_var("end-fork"))
        # consensus with local execution client
        if self.ccc is not None and self.ecc is not None:
            print("adding execution enviroment for consensus module")
            for ceev in self.consensus_with_execution_env_vars:
                environment.append(config_env.get_environment_var(ceev))
        # any additional env vars
        if self.cbc is not None:
            print("adding consensus bootnode enviroment for module")
            for bcbev in self.base_consensus_bootnode_env_vars:
                environment.append(config_env.get_environment_var(bcbev))

        if self.ebc is not None:
            print("adding consensus bootnode enviroment for module")
            for bebev in self.base_execution_bootnode_env_vars:
                environment.append(config_env.get_environment_var(bebev))

        if "additional-env" in self.cc:
            for k, v in self.cc["additional-env"].items():
                print(f"adding additional envs {k} {v}")
                environment.append(f'{k.upper().replace("-","_")}={v}')

        return list(set(environment))

    # inits for child classes.
    def config(self):
        out = {
            "container_name": self.name,
            "image": f"{self.image}:{self.tag}",
            "volumes": self.volumes,
            "networks": self._networking(),
        }
        if self.use_root:
            out["user"] = "root"
        return out

    def get_config(self):
        config = self.config()
        if "debug" in self.cc:
            if self.cc["debug"]:
                config["entrypoint"] = "/bin/bash"
                config["tty"] = True
                config["stdin_open"] = True
            else:
                config["entrypoint"] = self._entrypoint()
        else:
            config["entrypoint"] = self._entrypoint()
        print("doing enviroment")
        config["environment"] = self._environment()
        return config

    # # override this if neccessary
    # def _environment(self):
    #     return []

    def _networking(self):
        # first calculate the ip.
        return {self.network_name: {"ipv4_address": self.get_ip()}}

    def _entrypoint(self):
        if isinstance(self.cc["entrypoint"], str):
            return self.cc["entrypoint"].split()

        else:
            return self.cc["entrypoint"]

    def _config_sanity_check(self):
        """
        Sanity check and report exceptions for configs to help with people
        debugging their own configurations.
        """
        required_ccc_vars = [
            "num-nodes",  # how many beacon nodes
            "num-validators",  # how many validators across all nodes
            "start-consensus-p2p-port",  # the p2p port used by the beacon node
            "start-beacon-api-port",  # the port for the beacon rest api
            "start-beacon-rpc-port",  # some clients have seperate rpc ports
            "start-validator-rpc-port",  # the rpc port for the validator
            "start-beacon-metric-port",  # the port for the metric port
            "local-execution-client",  # if we have a local execution client
        ]
        # if there is a local execution client we must specify the following.
        required_ccc_if_lec = [
            "execution-config",  # the config for the execution client
            "execution-launcher",  # the launch script for the entrypoint
            "http-web3-ip-addr",  # local execution client http port
            "ws-web3-ip-addr",  # local execution client web-sockets port
        ]
        required_cc_vars = [
            "client-name",  # the name of the client, implemented are prysm/lightouse/teku/nimbus
            "image",  # the docker image for that client.
            "tag",  # docker image tag
            "container-name",  # name of the container
            "entrypoint",  # the entrypoint, examples in apps/launchers
            # ip address for client, incremented based on numnber of nodes.
            "start-ip-addr",
            "depends",  # ethereum-testnet-bootstrapper client.
            "consensus-config",  # the consensus client config (ccc)
            "testnet-dir",  # the testnet dir to use
            # the offset to use for validator keys (since we use same mnemonic)
            "validator-offset-start",
        ]
        # TODO: global config stuff and sanity checks on some vars.
        # client-configs
        for req_cc in required_cc_vars:
            if req_cc not in self.cc:
                raise Exception(
                    f"The client must implement {req_cc} see source comments"
                )

        for req_ccc in required_ccc_vars:
            if req_ccc not in self.ccc:
                raise Exception(
                    f"The consensus config must implement {req_ccc} see source comments"
                )
        if self.ccc["local-execution-client"]:
            for req_ccc in required_ccc_if_lec:
                if req_ccc not in self.ccc:
                    raise Exception(
                        f"The consensus config must implement {req_ccc} when using a local execution client."
                    )

    def get_ip(self, _unused="unused"):
        prefix = ".".join(self.cc["start-ip-addr"].split(".")[:3]) + "."
        base = int(self.cc["start-ip-addr"].split(".")[-1])
        ip = prefix + str(base + self.curr_node)
        return ip


class Eth2BootnodeClientWriter(ClientWriter):
    def __init__(self, global_config, client_config, curr_node):
        super().__init__(global_config, client_config, curr_node)
        self.out = self.config()

    def _entrypoint(self):
        """
        ./launch-bootnode <ip-address> <enr-port> <api-port> <private-key> <enr-path>
        launches a bootnode with a web port for fetching the enr, and
        fetches that enr and puts it in the local dir for other clients
        to find..
        """
        return [
            str(self.cc["entrypoint"]),
            str(self.get_ip()),
            str(self.cc["enr-udp"]),
            str(self.cc["api-port"]),
            str(self.cc["private-key"]),
            str(self.cc["bootnode-enr-file"]),
        ]


class ExecutionBootnodeClientWriter(ClientWriter):
    def __init__(self, global_config, client_config, curr_node):
        super().__init__(
            global_config, client_config, f"geth-bootnode-{curr_node}", curr_node
        )
        self.out = self.config()

    def _environment(self):
        environment = []
        config_env = ConfigurationEnvironment(self)
        # consensus client env vars
        for bebev in self.base_execution_bootnode_env_vars:
            environment.append(config_env.get_environment_var(bebev))


class GethBootnodeClientWriter(ClientWriter):
    def __init__(self, global_config, client_config, curr_node):
        super().__init__(
            global_config, client_config, f"geth-bootstrapper-{curr_node}", curr_node
        )
        self.out = self.config()

    def _entrypoint(self):
        """
        ./launch-bootnode <ip-address> <enr-port> <api-port> <private-key> <enr-path>
        launches a bootnode with a web port for fetching the enr, and
        fetches that enr and puts it in the local dir for other clients
        to find..
        """
        return [
            str(self.cc["entrypoint"]),
            str(self.cc["data-dir"]),
            self.get_ip(),
            self.get_port("execution-p2p"),
        ]


class GenericModule(ClientWriter):
    def __init__(self, global_config, client_config, curr_node):
        super().__init__(global_config, client_config, curr_node)
        self.out = self.config()

    def _entrypoint(self):
        if isinstance(self.cc["entrypoint"], str):
            return self.cc["entrypoint"].split()

        else:
            return self.cc["entrypoint"]


class TestnetBootstrapper(ClientWriter):
    def __init__(self, global_config, client_config):
        super().__init__(global_config, client_config, 0)
        self.out = self.config()

    def _entrypoint(self):
        return [
            "/source/entrypoint.sh",
            "--config",
            self.cc["config-file"],
            "--no-docker-compose",
        ]


class DockerComposeWriter(object):
    def __init__(self, global_config):
        self.gc = global_config
        self.yaml = self._base()
        self.client_writers = {
            "teku": ClientWriter,
            "prysm": ClientWriter,
            "lighthouse": ClientWriter,
            "lodestar": ClientWriter,
            "nimbus": ClientWriter,
            "geth-bootstrapper": ClientWriter,
            "ethereum-testnet-bootstrapper": TestnetBootstrapper,
            "generic-module": GenericModule,
            "eth2-bootnode": ClientWriter,
            "geth-bootnode": ClientWriter,
        }

    def _base(self):
        return {
            "services": {},
            "networks": {
                self.gc["docker"]["network-name"]: {
                    "driver": "bridge",
                    "ipam": {"config": [{"subnet": self.gc["docker"]["ip-subnet"]}]},
                }
            },
        }

    def add_services(self):
        # keep testnet-bootstrapper seperate
        client_modules = [
            "execution-clients",
            "generic-modules",
            "consensus-bootnodes",
            "execution-bootnodes",
        ]

        for module in client_modules:
            if module in self.gc:
                for client_module in self.gc[module]:
                    config = self.gc[module][client_module]
                    if not "client-name" in config:
                        exception = f"module {module}, {client_module} expects client-name attribute\n"
                        exception += f"\tfound: {config.keys()}\n"
                        raise Exception(exception)
                    client = config["client-name"]
                    print(f"Generating docker-compose entry for {client}")
                    for n in range(config["num-nodes"]):
                        if module == "generic-modules":
                            writer = self.client_writers["generic-module"](
                                self.gc, config, n
                            )
                        else:
                            writer = self.client_writers[client](self.gc, config, n)
                        self.yaml["services"][writer.name] = writer.get_config()

        for consensus_client in self.gc["consensus-clients"]:
            config = self.gc["consensus-clients"][consensus_client]
            consensus_config = self.gc["consensus-configs"][config["consensus-config"]]
            client = config["client-name"]
            print(f"Generating docker-compose entry for {client}")
            for n in range(consensus_config["num-nodes"]):
                if client == "teku":
                    use_root = True
                else:
                    use_root = False
                writer = self.client_writers[client](self.gc, config, n, use_root)
                self.yaml["services"][writer.name] = writer.get_config()
        # last we check for bootstrapper, if present all dockers must
        # depend on this.
        if "testnet-bootstrapper" in self.gc:
            for client in self.gc["testnet-bootstrapper"]:
                tbc = self.gc["testnet-bootstrapper"][client]
                tbw = self.client_writers[client](self.gc, tbc)
                for service in self.yaml["services"]:
                    self.yaml["services"][service]["depends_on"] = [tbw.name]
                self.yaml["services"][tbw.name] = tbw.get_config()


def generate_docker_compose(global_config):
    dcw = DockerComposeWriter(global_config)
    dcw.add_services()
    return dcw.yaml
