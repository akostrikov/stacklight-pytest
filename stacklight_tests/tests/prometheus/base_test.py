import logging

from stacklight_tests.clients.prometheus import prometheus_client
from stacklight_tests import objects
from stacklight_tests import utils

logger = logging.getLogger(__name__)


class BaseLMATest(object):
    @classmethod
    def setup_class(cls):
        cls.config = utils.load_config()
        # TODO(rpromyshlennikov): make types as enum?
        cls.env_type = cls.config.get("env", {}).get("type", "")
        cls.is_mk = cls.env_type == 'mk'

        nodes = cls.config.get("nodes")
        cls.cluster = objects.Cluster()

        for node_args in nodes:
            cls.cluster.add_host(
                objects.Host(**node_args)
            )

        prometheus_config = cls.config.get("prometheus")
        cls.prometheus_api = prometheus_client.PrometheusClient(
            "http://{0}:{1}/".format(prometheus_config["prometheus_vip"],
                                     prometheus_config["prometheus_server_port"])
        )

    def test_prometheus_container(self):
        prometheus_nodes = self.cluster.filter_by_role("prometheus")
        docker_services = \
            prometheus_nodes[0].exec_command(
                "docker service ls -f name=prometheus_server").splitlines()
        docker_services = docker_services[:-1]
        service_id, name, mode, replicas, image = docker_services.split()
        currnet, planned = replicas.split("/")
        print "Repliacs", int(currnet)
        for node in prometheus_nodes:
            status = node.exec_command(
                "docker ps --filter ancestor=prometheus "
                "--format '{{.Status}}'")
            print node.fqdn, "Prometheus", status, "Up" in status

    def test_k8s_metrics(self):
        print self.prometheus_api.get_query("kubelet_running_pod_count")

    def test_etcd_metrics(self):
        print self.prometheus_api.get_query("etcd_debugging_store_expires_total")

    def test_telegraf_metrics(self):
        print self.prometheus_api.get_query("system_uptime")

    def test_prometheus_metrics(self):
        print self.prometheus_api.get_query("prometheus_local_storage_series_ops_total")

    def test_system_metrics(self):
        print self.prometheus_api.get_query("system_load15")
