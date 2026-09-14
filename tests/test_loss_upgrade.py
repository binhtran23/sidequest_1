import copy
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.analyze_loss_cohort import analyze_seat, useful_days

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT/'agents/slices/kaggriculture-most-powerful-route/variants/loss_upgrade_v1/main.py'


def load(path):
    spec = importlib.util.spec_from_file_location('loss_test',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observation(day=19):
    farm = {'farmer':[4,4], 'hands':[], 'tiles':[[None]*10 for _ in range(10)],
            'money':0,'hires_today':0,'unlocked_quadrants':['NW']}
    farm['tiles'][4][4] = {'kind':'PLANT','crop':'STRAWBERRY','planted_day':8,
                          'fertilized_until_day':-1,'watered_today':True,
                          'yield_units':0,'consecutive_unwatered':0,'max_lifespan_step':-1}
    return {'player':0,'day':day,'hour':10,'step':day*24+10,
            'farms':[farm,copy.deepcopy(farm)],
            'private':{'inventories':[{'FERTILIZER':1}],'shed':{},'seeds':{}},
            'market':{'prices':{'STRAWBERRY':120,'FERTILIZER':50,'MILK':160}},
            'town':{'unlocked_shops':[]}}


def blank():
    return {'farmer':['PASS'],'hands':[],'market':[]}


class LossUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load(CANDIDATE)

    def setUp(self):
        self.policy._LOSS_SETTINGS = {'fertilizer':'window'}
        self.policy._LOSS_OBSERVATION = None
        self.policy._POLICY = SimpleNamespace(players={0:SimpleNamespace(plan=0)},
                                             tapes=[[blank() for _ in range(719)]])
        self.policy.drain_telemetry()

    def test_fertilizer_yield_matches_engine_refresh(self):
        from kaggle_environments.envs.kaggriculture import kaggriculture as engine
        obs = observation()
        action = blank()
        self.policy._loss_field_actions(obs,action)
        self.assertEqual(action['farmer'],['FERTILIZE'])
        farm = obs['farms'][0]
        engine._apply_unit_action(farm,obs['private'],0,action['farmer'],10,19,24)
        engine._daily_refresh_plants(farm,19,24)
        self.assertEqual(farm['tiles'][4][4]['yield_units'],2)

    def test_no_fertilizer_outside_finite_production_life(self):
        obs = observation(26)
        tile = obs['farms'][0]['tiles'][4][4]
        self.assertEqual(useful_days(tile,26),[])
        action = blank()
        self.policy._loss_field_actions(obs,action)
        self.assertEqual(action,blank())

    def test_maintenance_and_resources_take_priority(self):
        for case in ('unwatered','empty','expensive','covered','opening'):
            obs = observation()
            action = blank()
            tile = obs['farms'][0]['tiles'][4][4]
            if case == 'unwatered':
                tile['watered_today'] = False
                action['farmer'] = ['WATER']
            elif case == 'empty':
                obs['private']['inventories'][0] = {}
            elif case == 'expensive':
                obs['market']['prices']['FERTILIZER'] = 10000
            elif case == 'covered':
                tile['fertilized_until_day'] = obs['day'] + 2
            else:
                obs['day'],obs['step'] = 5,130
            original = copy.deepcopy(action)
            self.policy._loss_field_actions(obs,action)
            self.assertEqual(action,original,case)

    def test_sale_cash_and_hand_count_preserved_by_field_change(self):
        obs = observation()
        action = blank()
        action['market'] = [['SELL','FERTILIZER',10],['HIRE']]
        self.policy._loss_field_actions(obs,action)
        self.assertEqual(action['market'],[['SELL','FERTILIZER',10],['HIRE']])
        self.assertEqual(len(action['hands']),len(obs['farms'][0]['hands']))

    def test_scheduled_fertilizer_is_reserved_for_existing_work(self):
        obs = observation()
        self.policy._POLICY.tapes[0][obs['step']+2]['farmer'] = ['FERTILIZE']
        action = blank()
        self.policy._loss_field_actions(obs,action)
        self.assertEqual(action,blank())

    def test_fourth_turn_sale_requires_public_competing_output(self):
        p = self.policy
        obs = observation(12)
        obs['step'] = 309
        obs['private']['shed'] = {'MILK':6}
        obs['farms'][1]['tiles'][4][4] = None
        p._LOSS_OBSERVATION = obs
        p._LOSS_SETTINGS = {'sale_pressure':True}
        tape = [blank() for _ in range(719)]
        tape[313]['market'] = [['SELL','MILK',6]]
        for pressure in (False,True):
            if pressure:
                obs['farms'][1]['tiles'][2][2] = {'kind':'PASTURE','animal':'COW','yield_units':6}
            action = blank()
            state = SimpleNamespace(queues={},sale_window_debts={})
            p.reserve_sales(action,p.FarmView(obs),state,tape,309)
            self.assertEqual(action['market'],[['SELL','MILK',6]] if pressure else [])

    def test_fourth_turn_sale_uses_this_turns_drop_projection(self):
        p=self.policy
        obs=observation(12)
        obs['step']=309
        obs['private']['shed']={}
        obs['private']['inventories']=[{'MILK':6}]
        obs['farms'][1]['tiles'][2][2]={'kind':'PASTURE','animal':'COW','yield_units':6}
        p._LOSS_OBSERVATION=obs
        p._LOSS_SETTINGS={'sale_pressure':True}
        tape=[blank() for _ in range(719)]
        tape[313]['market']=[['SELL','MILK',6]]
        action=blank()
        action['farmer']=['DROP']
        state=SimpleNamespace(queues={},sale_window_debts={})
        p.reserve_sales(action,p.FarmView(obs),state,tape,309)
        self.assertEqual(action['market'],[['SELL','MILK',6]])
        self.assertEqual(obs['private']['shed'],{})

    def test_same_tile_fertilizer_claimed_only_once(self):
        obs = observation()
        obs['farms'][0]['hands'] = [[4,4]]
        obs['private']['inventories'].append({'FERTILIZER':1})
        action = blank()
        action['hands'] = [['PASS']]
        self.policy._loss_field_actions(obs,action)
        self.assertEqual(action['farmer'],['FERTILIZE'])
        self.assertEqual(action['hands'],[['PASS']])

    def test_late_harvest_respects_capacity_and_last_callback(self):
        self.policy._LOSS_SETTINGS = {'fertilizer':'none','late_harvest':True}
        obs = observation(29)
        obs['farms'][0]['tiles'][4][4] = {'kind':'PASTURE','animal':'COW','yield_units':6}
        action = blank()
        self.policy._loss_field_actions(obs,action)
        self.assertEqual(action['farmer'],['HARVEST'])
        for case in ('full','final'):
            action = blank()
            if case == 'full':
                obs['private']['shed'] = {'MILK':99}
            else:
                obs['private']['shed'] = {}
                obs['step'] = 718
            self.policy._loss_field_actions(obs,action)
            self.assertEqual(action,blank())

    def test_sale_window_reserves_pickups_and_stops_at_route_boundary(self):
        p = self.policy
        p.SALE_HORIZON = 4
        obs = observation(12)
        obs['step'] = 309
        obs['private']['shed'] = {'MILK':6}
        state = SimpleNamespace(queues={},sale_window_debts={})
        tape = [blank() for _ in range(719)]
        tape[313]['market'] = [['SELL','MILK',6]]
        action = blank()
        p.reserve_sales(action,p.FarmView(obs),state,tape,309)
        self.assertEqual(action['market'],[['SELL','MILK',6]])
        due = copy.deepcopy(tape[313])
        state.sale_due_step,state.advanced_sales = -1,{}
        p.subtract_advanced_sales(due,state,313)
        self.assertEqual(due['market'],[['SELL','MILK',0]])
        state.sale_window_debts = {}
        tape[312]['farmer'] = ['PICKUP','MILK',6]
        action = blank()
        p.reserve_sales(action,p.FarmView(obs),state,tape,309)
        self.assertEqual(action['market'],[])
        tape[360]['market'] = [['SELL','MILK',6]]
        action = blank()
        p.reserve_sales(action,p.FarmView(obs),state,tape,358)
        self.assertEqual(action['market'],[])

    def assert_disabled_matches_base(self, candidate, base):
        """With its settings cleared, a candidate must replay its own base exactly.

        The base is per-candidate, not root: `loss_upgrade_v1` was composed onto
        route-v1-h3 and so does not carry V227, which route-v2-fert18 added.
        Comparing it against today's root tests the promotion history, not parity.
        """
        files = sorted((ROOT/'evidence/raw/champion-losses-20260912').glob('*.json'))
        if not files:
            self.skipTest('Optional local replay evidence absent')
        import json
        replay = json.loads(files[0].read_text())
        p, reference = load(candidate), load(base)
        p._LOSS_SETTINGS = {}
        seat = replay['info']['TeamNames'].index('Bình Trần Thanh')
        for t, states in enumerate(replay['steps'][:-1]):
            obs = copy.deepcopy(states[seat]['observation'])
            obs['step'], obs['player'] = t, seat
            self.assertEqual(p.agent(copy.deepcopy(obs)), reference.agent(copy.deepcopy(obs)), t)

    def test_disabled_candidate_matches_its_route_v1_base(self):
        self.assert_disabled_matches_base(
            CANDIDATE, ROOT/'submission/route-v1-h3-20260912/main.py')

    def test_disabled_v3_matches_the_current_champion(self):
        candidate = (ROOT/'agents/slices/kaggriculture-most-powerful-route'
                     '/variants/sale_fert_v3/main.py')
        if not candidate.exists():
            self.skipTest('sale_fert_v3 has not been built')
        self.assert_disabled_matches_base(candidate, ROOT/'main.py')


if __name__ == '__main__':
    unittest.main()
