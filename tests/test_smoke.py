from tests import base_test


class TestSmoke(base_test.BaseLMATest):
    def test_logs_in_elasticsearch(self):
        """Check that logs of all known services are presented
        in Elasticsearch

        Scenario:
            1. Check that logs are collected for all known services
               to current Elasticsearch index

        Duration 15m
        """
        known_services = {
            'CRON', 'api', 'attrd',
            'cib',
            'cinder-api', 'cinder-backup', 'cinder-scheduler', 'cinder-volume',
            'crmd',
            'dhcp-agent',
            'glare',
            'haproxy',
            'heat-api', 'heat-api-cfn', 'heat-api-cloudwatch', 'heat-engine',
            'horizon_access',
            'keystone-admin', 'keystone-public',
            'keystone-wsgi-admin', 'keystone-wsgi-main',
            'l3-agent',
            'liberasurecode',
            'lrmd',
            'metadata-agent',
            'nagios3',
            'neutron-openvswitch-agent',
            'nova-api', 'nova-compute', 'nova-conductor', 'nova-scheduler',
            'ocf-mysql-wss', 'ocf-ns_IPaddr2', 'ocf-ns_apache(apache2-nagios)',
            'ocf-ns_conntrackd', 'ocf-ns_dns', 'ocf-ns_haproxy', 'ocf-ns_ntp',
            'ocf-ns_vrouter',
            'openvswitch-agent',
            'pengine',
            'registry',
            'server',
            'su',
            'swift-account-server', 'swift-container-server',
            'swift-object-server', 'swift-proxy-server',
            'xinetd'
        }
        # NOTE(some services, available only after deploy)
        # after_deploy_services = {
        #     'dnsmasq', 'dnsmasq-dhcp',
        #     'kernel',
        #     'ntpd', 'ntpdate',
        #     'ovs-vswitchd',
        #     'rabbitmq',
        #     'sshd',
        #
        # }
        for service in known_services:
            output = self.es_kibana_api.query_elasticsearch(
                index_type="log",
                query_filter="programname:{service}".format(service=service))
            assert output['hits']['total'] != 0, (
                "Indexes don't contain {service} logs".format(service=service))

    def test_display_grafana_dashboards_toolchain(self):
        """Verify that the dashboards show up in the Grafana UI.

        Scenario:
            1. Go to the Main dashboard and verify that everything is ok
            2. Repeat the previous step for the following dashboards:
                * Apache
                * Cinder
                * Elasticsearch
                * Glance
                * HAProxy
                * Heat
                * Hypervisor
                * InfluxDB
                * Keystone
                * LMA self-monitoring
                * Memcached
                * MySQL
                * Neutron
                * Nova
                * RabbitMQ
                * System

        Duration 20m
        """
        self.grafana_api.check_grafana_online()
        dashboard_names = {
            "Apache", "Cinder", "Elasticsearch", "Glance", "HAProxy", "Heat",
            "Hypervisor", "InfluxDB", "Keystone", "LMA self-monitoring",
            "Memcached", "MySQL", "Neutron", "Nova", "RabbitMQ", "System"
        }
        dashboard_names = {panel_name.lower().replace(" ", "-")
                           for panel_name in dashboard_names}

        available_dashboards_names = set()
        for name in dashboard_names:
            if self.grafana_api.is_dashboard_exists(name):
                available_dashboards_names.add(name)
        msg = ("There is not enough panels in available panels, "
               "panels that are not presented: {}")
        assert dashboard_names == available_dashboards_names, (
            msg.format(dashboard_names - available_dashboards_names))

    def test_openstack_service_metrics_presented(self):
        metrics = {
            "openstack_check_api",
            "openstack_check_local_api",
            "openstack_cinder_http_response_times",
            "openstack_cinder_service",
            "openstack_cinder_services",
            "openstack_cinder_services_percent",
            "openstack_cinder_volume_attachment_time",
            "openstack_cinder_volume_creation_time",
            "openstack_cinder_volumes",
            "openstack_cinder_volumes_size",
            "openstack_glance_http_response_times",
            "openstack_glance_images",
            "openstack_glance_images_size",
            "openstack_glance_snapshots",
            "openstack_heat_http_response_times",
            "openstack_keystone_http_response_times",
            "openstack_keystone_roles",
            "openstack_keystone_tenants",
            "openstack_keystone_users",
            "openstack_neutron_agent",
            "openstack_neutron_agents",
            "openstack_neutron_agents_percent",
            "openstack_neutron_http_response_times",
            "openstack_neutron_networks",
            "openstack_neutron_ports",
            "openstack_neutron_routers",
            "openstack_neutron_subnets",
            "openstack_nova_free_disk",
            "openstack_nova_free_ram",
            "openstack_nova_free_vcpus",
            "openstack_nova_http_response_times",
            "openstack_nova_instance_creation_time",
            "openstack_nova_instance_state",
            "openstack_nova_instances",
            "openstack_nova_running_instances",
            "openstack_nova_running_tasks",
            "openstack_nova_service",
            "openstack_nova_services",
            "openstack_nova_services_percent",
            "openstack_nova_total_free_disk",
            "openstack_nova_total_free_ram",
            "openstack_nova_total_free_vcpus",
            "openstack_nova_total_running_instances",
            "openstack_nova_total_running_tasks",
            "openstack_nova_total_used_disk",
            "openstack_nova_total_used_ram",
            "openstack_nova_total_used_vcpus",
            "openstack_nova_used_disk",
            "openstack_nova_used_ram",
            "openstack_nova_used_vcpus",
        }
        measurements = (
            self.influxdb_api.do_influxdb_query("show measurements").json())
        measurements = {item[0] for item in
                        measurements['results'][0]["series"][0]["values"]
                        if item[0].startswith("openstack")}
        assert metrics == measurements

    def test_openstack_services_alarms_presented(self):
        tables = ("openstack_check_api",
                  "openstack_check_local_api",)
        services = (
            "cinder-api",
            "cinder-v2-api",
            "glance-api",
            "heat-api",
            "heat-cfn-api",
            "keystone-public-api",
            "neutron-api",
            "nova-api",
            "swift-api",
            "swift-s3-api",
        )
        query = ("select last(value) "
                 "from {table} "
                 "where time >= now() - 1m and service = '{service}'")
        for table in tables:
            for service in services:
                query = query.format(table=table, service=service)
                assert len(self.influxdb_api.do_influxdb_query(
                    query).json()['results'][0])
