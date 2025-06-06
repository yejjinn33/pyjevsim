import random
import datetime
from pyjevsim import BehaviorModel, Infinite
from pyjevsim.system_message import SysMessage

class CommandControl(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Decision", 0)

        self.insert_input_port("threat_list")
        self.insert_output_port("launch_order")

        self.threat_list = []

    def generate_random_decoy_plan(self):
        plan = []
        base_heading = random.randint(0, 360)
        for i in range(1): 
            if random.random() < 0.5:
                plan.append({
                    "type": "stationary",
                    "lifespan": random.randint(5, 15),
                    "elevation": random.choice([0, 5, 10]),
                    "azimuth": random.randint(0, 360),
                    "speed": random.randint(5, 10),
                })
            else:
                plan.append({
                    "type": "self_propelled",
                    "lifespan": random.randint(10, 20),
                    "elevation": random.choice([0, 10]),
                    "azimuth": random.randint(0, 360),
                    "speed": random.randint(5, 10),
                    "heading": (base_heading + i * 15) % 360,
                    "xy_speed": random.randint(4, 8),
                })

        print(f"[{self.get_name()}][Generated Decoy Plan]:")
        for idx, d in enumerate(plan):
            print(f"  - Decoy[{idx}]: {d}")

        return plan

    def ext_trans(self, port, msg):
        if port == "threat_list":
            print(f"{self.get_name()}[threat_list]: {datetime.datetime.now()}")
            self.threat_list = msg.retrieve()[0]
            self._cur_state = "Decision"

    def output(self, msg):
        for target in self.threat_list:
            if self.platform.co.threat_evaluation(self.platform.mo, target):
                if not hasattr(self.platform.lo, "decoy_queue") or not self.platform.lo.decoy_queue:
                    self.platform.lo.get_decoy_list = self.generate_random_decoy_plan
                    self.platform.lo.decoy_queue = self.generate_random_decoy_plan()

                if self.platform.lo.decoy_queue:
                    msg.insert_message(SysMessage(self.get_name(), "launch_order"))

                self.platform.mo.change_heading(self.platform.co.get_evasion_heading())

        self.threat_list = []
        return msg

    def int_trans(self):
        if self._cur_state == "Decision":
            self._cur_state = "Wait"
