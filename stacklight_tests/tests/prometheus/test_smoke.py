import pytest
import socket


class TestPrometheusSmoke(object):
    def test_prometheus_container(self, cluster):
        prometheus_nodes = cluster.filter_by_role("prometheus")

        def test_prometheus_container_up(node):
            status = node.exec_command(
                "docker ps --filter name=monitoring_server "
                "--format '{{.Status}}'")
            return "Up" in status

        assert any([test_prometheus_container_up(node)
                    for node in prometheus_nodes])

    def test_prometheus_datasource(self, prometheus_api):
        assert prometheus_api.get_all_measurements()

    def test_prometheus_relay(self, salt_actions):
        hosts = salt_actions.ping("I@prometheus:relay")
        if not hosts:
            pytest.skip("Prometheus relay is not installed in the cluster")
        url = salt_actions.get_pillar_item(
            '*', "_param:grafana_prometheus_address")[0]
        port = salt_actions.get_pillar_item(
            hosts[0], "prometheus:relay:bind:port")[0]
        output = salt_actions.run_cmd(
            hosts[0],
            "curl -s {}:{}/metrics | awk '/^prometheus/{{print $1}}'".format(
                url, port))
        assert output


class TestAlertmanagerSmoke(object):
    def test_alertmanager_endpoint_availability(self, prometheus_config):
        """Check that alertmanager endpoint is available.

        Scenario:
            1. Get alertmanager endpoint
            2. Check that alertmanager endpoint is available
        Duration 1m
        """
        port = int(prometheus_config["prometheus_alertmanager"])
        alertmanager_ip = prometheus_config["prometheus_vip"]
        try:
            s = socket.socket()
            s.connect((alertmanager_ip, port))
            s.close()
            result = True
        except socket.error:
            result = False
        assert result

    def test_alertmanager_ha(self, cluster, prometheus_config):
        """Check alertmanager HA .

        Scenario:
            1. Stop 1 alertmanager replic
            2. Get alertmanager endpoint
            3. Check that alertmanager endpoint is available
        Duration 1m
        """
        prometheus_nodes = cluster.filter_by_role("prometheus")
        for host in prometheus_nodes:
            alertmanager_docker_id = host.exec_command(
                "docker ps | grep alertmanager | awk '{print $1}'")
            if alertmanager_docker_id:
                command = "docker kill " + str(alertmanager_docker_id)
                host.exec_command(command)
                return TestAlertmanagerSmoke. \
                    test_alertmanager_endpoint_availability(self,
                                                            prometheus_config)
