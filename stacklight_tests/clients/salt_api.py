import salt.client


class SaltApi(object):
    def __init__(self):
        self.salt_api = salt.client.LocalClient()

    def run_cmd(self, tgt, command, tgt_type='compound'):
        return self.salt_api.cmd(
            tgt, "cmd.run", [command], tgt_type=tgt_type).values()

    def ping(self, tgt='*', tgt_type='compound'):
        nodes = self.salt_api.cmd(tgt, "test.ping", tgt_type=tgt_type).keys()
        return nodes

    def get_pillar(self, tgt, pillar, tgt_type='compound'):
        result = self.salt_api.cmd(
            tgt, 'pillar.get', [pillar], tgt_type=tgt_type)
        return result

    def get_pillar_item(self, tgt, pillar_item, tgt_type='compound'):
        result = self.salt_api.cmd(
            tgt, 'pillar.get', [pillar_item], tgt_type=tgt_type).values()
        return [i for i in result if i]

    def get_grains(self, tgt, grains, tgt_type='compound'):
        result = self.salt_api.cmd(
            tgt, 'grains.get', [grains], tgt_type=tgt_type)
        return result
