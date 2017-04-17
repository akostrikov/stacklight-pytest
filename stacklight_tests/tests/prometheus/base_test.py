import logging
from pprint import pprint

from stacklight_tests.clients.prometheus import prometheus_client
from stacklight_tests import objects
from stacklight_tests import utils

logger = logging.getLogger(__name__)


class BaseLMATest(object):
    @classmethod
    def setup_class(cls):
        cls.config = utils.load_config()

        nodes = cls.config.get("ssh")
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

class TestProm(BaseLMATest):

    def test_prometheus_container(self):
        prometheus_nodes = self.cluster.filter_by_role("prometheus")
        docker_services = \
            prometheus_nodes[0].exec_command(
                "docker service ls -f name=monitoring_server").splitlines()
        print docker_services
        docker_services = docker_services[1]
        service_id, name, mode, replicas, image = docker_services.split()
        currnet, planned = replicas.split("/")
        print "Repliacs", int(currnet)
        for node in prometheus_nodes:
            status = node.exec_command(
                "docker ps --filter ancestor=prometheus "
                "--format '{{.Status}}'")
            print node.fqdn, "Prometheus", status, "Up" in status

    def test_k8s_metrics(self):
        nodes = self.cluster.filter_by_role("kubernetes")
        expected_hostnames = [node.fqdn.split(".")[0] for node in nodes]
        unexpected_hostnames = []
   
        metrics = self.prometheus_api.get_query("kubelet_running_pod_count")

        for metric in metrics:
            hostname = metric["metric"]["instance"]
            try:
                expected_hostnames.remove(hostname)
            except ValueError:
                unexpected_hostnames.append(hostname)
        assert unexpected_hostnames == []
        assert expected_hostnames == []

    def test_etcd_metrics(self):
        nodes = self.cluster.filter_by_role("etcd")
        expected_hostnames = [node.address for node in nodes]
        unexpected_hostnames = []

        metrics = self.prometheus_api.get_query("kubelet_running_pod_count")

        for metric in metrics:
            hostname = metric["metric"]["instance"].split(":")[0]
            try:
                expected_hostnames.remove(hostname)
            except ValueError:
                unexpected_hostnames.append(hostname)
        assert unexpected_hostnames == []
        assert expected_hostnames == []
      
    def test_telegraf_metrics(self):
        nodes = self.cluster.filter_by_role("telegraf")
        expected_hostnames = [node.fqdn.split(".")[0] for node in nodes]
        unexpected_hostnames = []

        metrics = self.prometheus_api.get_query("system_uptime")

        for metric in metrics:
            hostname = metric["metric"]["host"]
            try:
                expected_hostnames.remove(hostname)
            except ValueError:
                unexpected_hostnames.append(hostname)
        assert unexpected_hostnames == []
        assert expected_hostnames == []

    def test_prometheus_metrics(self):
        metric = self.prometheus_api.get_query("prometheus_local_storage_series_ops_total")
        assert len(metric) != 0

#    def test_system_metrics(self):
#        nodes = self.cluster.filter_by_role("telegraf")
#        node_hostnames = [node.fqdn.split(".")[0] for node in nodes]
#        print node_hostnames
#        pprint(self.prometheus_api.get_query("system_load15"))
