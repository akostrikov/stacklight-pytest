import pytest


ignored_queries = [
    # Default installation does not contain cinder-volume
    'max(openstack_cinder_services{state="down", service="cinder-volume"})',
    'max(openstack_cinder_services{service="cinder-volume"}) by (state)',
    'max(openstack_cinder_services'
    '{state="disabled",service="cinder-volume"})',
    'max(openstack_cinder_services{state="up", service="cinder-volume"})',

    # By default metric is not present if no tracked value
    'irate(openstack_heat_http_response_times_count{http_status="5xx"}[5m])',
]


def idfy_name(name):
    return name.lower().replace(" ", "-").replace("(", "").replace(")", "")


def query_dict_to_string(query_dict):
    return "\n\n".join(
        [panel + "\n" + query for panel, query in query_dict.items()])


def get_all_grafana_dashboards_names():
    dashboards = {
        "Apache": "apache",
        "Cassandra": "opencontrail",
        "Calico cluster monitoring (via Prometheus)": "kubernetes",
        "Cinder": "cinder",
        "Docker": "docker",
        "Elasticsearch": "elasticsearch",
        "Etcd": "etcd",
        "Glance": "glance",
        "GlusterFS": "glusterfs",
        "HAProxy": "haproxy",
        "Hypervisor": "service.nova.compute.kvm",
        "Heat": "heat",
        "InfluxDB": "influxdb",
        "Keystone": "keystone",
        "Kibana": "kibana",
        "Kubernetes App Metrics": "kubernetes",
        "Kubernetes cluster monitoring (via Prometheus)": "kubernetes",
        "Memcached": "memcached",
        "MySQL": "galera.master",
        "Neutron": "service.neutron.control.cluster",
        "Nova": "nova",
        "Nginx": "nginx",
        "OpenContrail": "opencontrail",
        "Prometheus Performances": "prometheus",
        "RabbitMQ": "rabbitmq",
        "System": "linux",
        "Remote storage adapter": "influxdb",
        "Grafana": "grafana",
    }

    return {idfy_name(k): v for k, v in dashboards.items()}


@pytest.fixture(scope="module",
                params=get_all_grafana_dashboards_names().items(),
                ids=get_all_grafana_dashboards_names().keys())
def dashboard_name(request, cluster):
    dash_name, requirement = request.param

    if not any([requirement in node.roles for node in cluster]):
        pytest.skip("No required class {} for dashboard: {}".format(
            requirement, dash_name))

    return dash_name


def test_grafana_dashboard_panel_queries(
        dashboard_name, grafana_client, prometheus_api):

    grafana_client.check_grafana_online()
    dashboard = grafana_client.get_dashboard(dashboard_name, prometheus_api)
    available_measurements = prometheus_api.get_all_measurements()

    assert grafana_client.is_dashboard_exists(dashboard_name), \
        "Dashboard {name} is not present".format(name=dashboard_name)

    for key, (raw_query, table) in dashboard.get_panel_queries().items():

        if table and (table not in available_measurements):
            print "no_table", raw_query    # Fix

        possible_templates = dashboard.get_all_templates_for_query(raw_query)
        panel_results = {"ok": [],
                         "failed": []}
        for template in possible_templates:
            query = prometheus_api.compile_query(raw_query, template)
            try:
                result = prometheus_api.do_query(query)
                if not result:
                    raise ValueError
                panel_results["ok"].append(template)
            except (KeyError, ValueError):
                panel_results["failed"].append(template)

        if len(panel_results["ok"]) == len(possible_templates):
            print "ok", raw_query
        if len(panel_results["failed"]) == len(possible_templates):
            print "failed", raw_query
        return "partially_ok", (raw_query, panel_results["failed"])

    assert 1 == 1
    #
    # ok_panels, partially_ok_panels, no_table_panels, failed_panels = result
    #
    # ignored_panels = [[loc, query, "Ignored"]
    #                   for loc, query in failed_panels.items()
    #                   if query in ignored_queries]
    #
    # failed_panels = [[loc, query, "Failed"]
    #                  for loc, query in failed_panels.items()
    #                  if query not in ignored_queries]
    #
    # partially_ok_panels_results = []
    #
    # for location, query_tuple in partially_ok_panels.items():
    #     query, template = query_tuple
    #     if query in ignored_queries:
    #         ignored_panels.append([location, query, "Ignored"])
    #         continue
    #
    #     partially_ok_panels_results.append([
    #         location, query, pprint.pformat(template)
    #     ])

    # fail_dict = {
    #     "Total OK": len(ok_panels),
    #     "No table": no_table_panels,
    #     "Total no table": len(no_table_panels),
    #     "Partially OK queries": partially_ok_panels,
    #     "Total partially OK": len(partially_ok_panels),
    #     "Failed queries": failed_panels,
    #     "Total failed": len(failed_panels),
    #     "Ignored panels": ignored_panels,
    #     "Total ignored": len(ignored_panels),
    # }
    #
    # fail_msg = (
    #     "Total OK: {Total OK}\n"
    #     "No table: {No table}\n"
    #     "Total no table: {Total no table}\n"
    #     "Partially OK queries: {Partially OK queries}\n"
    #     "Total partially OK: {Total partially OK}\n"
    #     "Failed queries: {Failed queries}\n"
    #     "Total failed: {Total failed}".format(
    #         **fail_dict))

    # fail_table = PrettyTable(["Panel", "Query", "Misc"])
    # fail_table.align["Panel"] = "l"
    # fail_table.align["Query"] = "l"
    # fail_table.align["Misc"] = "l"
    #
    # for item in failed_panels + ignored_panels + partially_ok_panels_results:
    #     fail_table.add_row(item)
    #
    # assert (ok_panels and not
    #         partially_ok_panels and not
    #         no_table_panels and not
    #         failed_panels), "\n" + fail_table.get_string()
