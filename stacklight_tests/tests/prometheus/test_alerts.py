import logging
import pytest

logger = logging.getLogger(__name__)


class TestPrometheusAlerts(object):
    def test_system_load_alerts(self, cluster, prometheus_alerting):
        """Check that alert for load overage and idle on node can be fired.

        Scenario:
            1. Check that alert is not fired
            2. Make high load on compute node during 5 minutes
            3. Wait until and check that alert was fired
            4. Unload compute node
            5. Wait until and check that alert was ended

        Duration 15m
        """
        def check_status(is_fired=True):
            alert_names = ["SystemLoad5", "AvgCPUUsageIdle"]
            for alert_name in alert_names:
                criteria = {
                    "name": alert_name,
                    "host": compute.hostname,
                }
                prometheus_alerting.check_alert_status(
                    criteria, is_fired=is_fired, timeout=6 * 60)

        load_processes_count = 20

        # TODO(rpromyshlennikov): use ".get_random_compute" method
        # instead of current filter after roles config of hosts will be fixed
        compute = [host for host in cluster.hosts
                   if host.fqdn.startswith("cmp")][0]

        check_status(is_fired=False)
        with compute.os.make_temporary_load(load_processes_count):
            check_status()
        check_status(is_fired=False)

    def test_system_mem_alert(self, cluster, prometheus_alerting):
        """Check that operation system alerts can be fired.
         Scenario:
            1. Check that alert is not fired
            2. Install 'stress' package
            3. start process which will to load mem
            4. Wait until and check that alert was fired
            5. Remove 'stress' package
            6. Wait until and check that alert was ended
        Duration 15m
        """
        cmp = cluster.filter_by_role("compute")[0]
        criteria = {
            "name": "AvgMemAvailablePercent",
            "service": "system",
        }
        cmp.os.apt_get_install_package("stress")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=10 * 60)
        memory = cmp.exec_command("grep MemFree /proc/meminfo")
        _, memory, _ = memory.split()
        memory = str(int(memory) * 0.95)
        command = "nohup stress --vm-bytes " + memory + "k --vm-keep -m 1" \
                  " --timeout 600 &"
        cmp.exec_command(command)
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=10 * 60)
        cmp.os.apt_get_remove_package("stress")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=10 * 60)

    def test_predict_linear_disk_inodes_free_alert(
            self, cluster, prometheus_alerting):
        """Check that operation system alerts can be fired.
         Scenario:
            1. Check that alert is not fired
            3. Create files 400000 /dev/shm
            4. Wait until and check that alert was fired
            5. Remove all files from /dev/shm
            6. Wait until and check that alert was ended

        Duration 15m
        """
        cmp = cluster.filter_by_role("compute")[0]
        criteria = {
            "name": "PredictLinearDiskInodesFree",
            "service": "system",
        }
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=10 * 60)
        cmp.exec_command("cd /dev/shm; for i in {1..4} ;do touch {$i}a{000001..100000}.c; done")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=10 * 60)
        remove_files = "cd /dev/shm; find . -name '*.c' -print0 | xargs -0 rm"
        cmp.exec_command(remove_files)
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=15 * 60)


class TestKubernetesAlerts(object):
    @pytest.mark.parametrize(
        "service", ["kube-proxy", "kube-apiserver", "kube-controller-manager",
                    "kubelet", "kube-scheduler"])
    def test_kubernetes_alert(self, cluster, prometheus_alerting, service):
        """Check that alerts for kubernetes services can be fired.

        Scenario:
            1. Check that alert is not fired
            2. Stop the corresponding kubernetes service on controller node
            3. Wait until and check that alert was fired
            4. Start the kubernetes service
            5. Wait until and check that alert was ended

        Duration 30m
        """
        ctl = cluster.get_controllers()[0]
        criteria = {
            "name": "ProcstatRunningKubernetes",
            "host": ctl.hostname,
        }
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)
        ctl.os.manage_service(service, "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=6 * 60)
        ctl.os.manage_service(service, "start")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)


class TestCalicoAlerts(object):
    def test_calico_alert(self, cluster, prometheus_alerting):
        """Check that alerts for calico services can be fired.
         Scenario:
            1. Check that alert is not fired
            2. Stop calico-node service on controller node
            3. Wait until and check that alert was fired
            4. Start calico-node service
            5. Wait until and check that alert was ended

        Duration 10m
        """
        ctl = cluster.get_controllers()[0]
        criteria = {
            "name": "ProcstatRunningCalico",
            "host": ctl.hostname,
        }
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)
        ctl.os.manage_service("calico-node", "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=6 * 60)
        ctl.os.manage_service("calico-node", "start")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)


class TestEtcdAlerts(object):
    def test_etcd_alert(self, cluster, prometheus_alerting):
        """Check that alerts for etcd services can be fired.
         Scenario:
            1. Check that alert is not fired
            2. Stop etcd service on controller node
            3. Wait until and check that alert was fired
            4. Start etcd service
            5. Wait until and check that alert was ended

        Duration 10m
        """
        ctl = cluster.get_controllers()[0]
        criteria = {
            "name": "EtcdClusterSmall",
            "service": "etcd",
        }
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)
        ctl.os.manage_service("etcd", "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=6 * 60)
        ctl.os.manage_service("etcd", "start")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)


class TestElasticSearchAlerts(object):
    def test_es_health_alert(self, cluster, prometheus_alerting):
        monitoring_nodes = cluster.filter_by_role("monitoring")[:2]
        criteria = {
            "name": "elasticsearch_cluster_health",
            "service": "elasticsearch",
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        criteria.update({"severity": "warning"})
        for mon_node in monitoring_nodes:
            mon_node.os.manage_service("elasticsearch", "stop")
            prometheus_alerting.check_alert_status(
                criteria, is_fired=True, timeout=6 * 60)
            criteria.update({"severity": "critical"})
        for mon_node in monitoring_nodes:
            mon_node.os.manage_service("elasticsearch", "start")
        del(criteria["severity"])
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)


class TestKeystoneAlerts(object):
    def test_keystone_alert(self, cluster, prometheus_alerting):
        """Check that alerts for keystone services can be fired.
         Scenario:
            1. Check that alert is not fired
            2. Stop apache2 services on nodes with keystone roll
            3. Wait until and check that alert was fired
            4. Start apache2 services on nodes with keystone roll
            5. Wait until and check that alert was ended

        Duration 15m
        """
        keystone_nodes = cluster.filter_by_role("keystone")
        criteria = {
            "name": "KeystoneAPIDown",
            "service": "keystone-public-api",
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        for key_node in keystone_nodes:
            key_node.os.manage_service("apache2", "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=10 * 60)
        for key_node in keystone_nodes:
            key_node.os.manage_service("apache2", "start")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=10 * 60)                                                       


class TestInfluxDBAlerts(object):
    def test_procstat_running_influxdb_alert(self, cluster, prometheus_alerting):
        """Check that alerts ProcstatRunningInfluxdb can be fired.
         Scenario:
            1. Check that alert is not fired
            2. Stop all influxdb services on controller node
            3. Wait until and check that alert was fired
            4. Start all influxdb services
            5. Wait until and check that alert was ended

        Duration 10m
        """
        influx_nodes = cluster.filter_by_role("influxdb")
        criteria = {
            "name": "ProcstatRunningInfluxdb",
            "service": "influxdb",
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        for inf_node in influx_nodes:
            inf_node.os.manage_service("influxdb", "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=6 * 60)
        for inf_node in influx_nodes:
            inf_node.os.manage_service("influxdb", "start")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)

    def test_influxdb_httpclient_error_alert(self, cluster, prometheus_alerting):
        """Check that alerts InfluxdbHTTPClientError can be fired.
         Scenario:
            1. Check that alert is not fired
            2. Create 6000 failed requests in influxdb
            3. Wait until and check that alert was fired
            4. Wait until and check that alert was ended

        Duration 10m
        """
        infl_node = cluster.filter_by_role("influxdb")[0]
        criteria = {
            "name": "InfluxdbHTTPClientError",
            "service": "influxdb",
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        command = "for i in {1..6000}; do influx -host " + str(
            infl_node.address) + " -port 8086 -database lma -username lma" \
                                 " -password lmapass -execute 'show tables'" \
                                 " &>/dev/null; done"
        infl_node.exec_command(command)
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=6 * 60)
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)


class TestMemcachedAlerts(object):
    def test_procstat_running_memcached_alert(self, cluster, prometheus_alerting):
        memcached_nodes = cluster.filter_by_role("memcached")
        criteria = {
            "name": "ProcstatRunningMemcached",
            "service": "memcached",
        }
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)
        for mem_node in memcached_nodes:
            mem_node.os.manage_service("memcached", "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=6 * 60)
        for mem_node in memcached_nodes:
            mem_node.os.manage_service("memcached", "start")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)                                                         


class TestNeutronAlerts(object):
    def test_neutron_api_alert(self, destructive, cluster,
                               prometheus_alerting):
        service = "neutron-server"
        controllers = cluster.get_controllers()
        criteria = {
            "name": "NeutronAPIDown",
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        criteria.update({"severity": "down"})
        logger.info("Stop {} service on {} nodes".format(
            service, ', '.join([str(ctl.hostname) for ctl in controllers])))
        for controller in controllers:
            destructive.append(
                lambda: controller.os.manage_service(service, "start"))
            controller.os.manage_service(service, "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=10 * 60)
        for controller in controllers:
            controller.os.manage_service(service, "start")
        del(criteria["severity"])
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=10 * 60)

    def test_neutron_all_agents_down_alert(self, cluster, destructive,
                                           prometheus_alerting):
        service = "neutron-l3-agent"
        hosts = [host for host in cluster.hosts if host.os.check_process(
            service)]
        criteria = {
            "name": "NeutronAllAgentsDown",
            "service": service,
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        criteria.update({"severity": "down"})
        logger.info("Stop {} service on {} nodes".format(
            service, ', '.join([str(h.hostname) for h in hosts])))
        for host in hosts:
            destructive.append(
                lambda: host.os.manage_service(service, "start"))
            host.os.manage_service(service, "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=10 * 60)
        for host in hosts:
            host.os.manage_service(service, "start")
        del(criteria["severity"])
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=10 * 60)

    def test_neutron_only_one_agent_up_alert(self, cluster, destructive,
                                             prometheus_alerting):
        service = "neutron-metadata-agent"
        hosts = [host for host in cluster.hosts if host.os.check_process(
            service)][:-1]
        criteria = {
            "name": "NeutronOnlyOneAgentUp",
            "service": service,
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        criteria.update({"severity": "critical"})
        logger.info("Stop {} service on {} nodes".format(
            service, ', '.join([str(h.hostname) for h in hosts])))
        for host in hosts:
            destructive.append(
                lambda: host.os.manage_service(service, "start"))
            host.os.manage_service(service, "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=10 * 60)
        for host in hosts:
            host.os.manage_service(service, "start")
        del(criteria["severity"])
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=10 * 60)

    def test_neutron_some_agents_down_alert(self, cluster, destructive,
                                            prometheus_alerting):
        service = "neutron-openvswitch-agent"
        host = [h for h in cluster.hosts if h.os.check_process(service)][0]
        criteria = {
            "name": "NeutronSomeAgentsDown",
            "service": service,
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        criteria.update({"severity": "warning"})
        logger.info("Stop {} service on {} node".format(
            service, host.hostname))
        destructive.append(lambda: host.os.manage_service(
            service, "start"))
        host.os.manage_service(service, "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=10 * 60)
        host.os.manage_service(service, "start")
        del(criteria["severity"])
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=10 * 60)


class TestGlanceAlerts(object):
    def test_glance_api_down_alert(self, cluster, prometheus_alerting):
        monitoring_nodes = cluster.filter_by_role("glance")
        criteria = {
            "name": "GlanceAPIDown",
            "service": "glance-api",
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        for mon_node in monitoring_nodes:
            mon_node.os.manage_service("glance-api", "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=6 * 60)
        for mon_node in monitoring_nodes:
            mon_node.os.manage_service("glance-api", "start")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)


class TestCinderAlerts(object):
    def test_cinder_api_down_alert(self, cluster, prometheus_alerting):
        monitoring_nodes = cluster.filter_by_role("cinder")
        criteria = {
            "name": "CinderAPIDown",
            "service": "cinder-api",
        }
        prometheus_alerting.check_alert_status(criteria, is_fired=False)
        for mon_node in monitoring_nodes:
            mon_node.os.manage_service("cinder-api", "stop")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=True, timeout=6 * 60)
        for mon_node in monitoring_nodes:
            mon_node.os.manage_service("cinder-api", "start")
        prometheus_alerting.check_alert_status(
            criteria, is_fired=False, timeout=6 * 60)

