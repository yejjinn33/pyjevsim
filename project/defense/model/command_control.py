import random
import datetime
import math
from pyjevsim import BehaviorModel, Infinite
from pyjevsim.system_message import SysMessage
from utils.object_db import ObjectDB

def get_distance(obj1, obj2):
    """두 객체 간 유클리디안 거리 계산"""
    x1, y1, z1 = obj1.get_position()
    x2, y2, z2 = obj2.get_position()
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2 + (z1 - z2)**2)

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

        self.current_cost = 0           # 누적된 디코이 발사 비용
        self.cost_limit = 10           # 총 비용 제한
        self.cost_exceeded = False  

    def get_decoy_cost(self, decoy):
        return 1 if decoy["type"] == "stationary" else 2.5

    def generate_random_decoy_plan(self):
        plan = []
        base_heading = random.randint(0, 360)

        for i in range(1):  # 하나씩만 발사
            if random.random() < 0.5:
                d = {
                    "type": "stationary",
                    "lifespan": random.randint(5, 15),
                    "elevation": random.choice([0, 5, 10]),
                    "azimuth": random.randint(0, 360),
                    "speed": random.randint(5, 10),
                }
            else:
                d = {
                    "type": "self_propelled",
                    "lifespan": random.randint(10, 20),
                    "elevation": random.choice([0, 10]),
                    "azimuth": random.randint(0, 360),
                    "speed": random.randint(5, 10),
                    "heading": (base_heading + i * 15) % 360,
                    "xy_speed": random.randint(4, 8),
                }

            cost = self.get_decoy_cost(d)

            if self.current_cost + cost >= self.cost_limit:
                if not self.cost_exceeded:
                    print(f"[{self.get_name()}]  디코이 비용 초과 → 추가 발사 중단 (총 비용 {self.current_cost})")
                    self.cost_exceeded = True
                return []
            else:
                self.current_cost += cost
                plan.append(d)

        print(f"[{self.get_name()}][Generated Decoy Plan] (누적 비용: {self.current_cost}):")
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
                dist_main = get_distance(self.platform.mo, target)

                decoys = [d[1] for d in ObjectDB().decoys]
                dist_decoy = min(
                    (get_distance(d, target) for d in decoys), default=float('inf')
                )

                print(f"[{self.get_name()}] 본선 거리: {dist_main:.2f}, 디코이 거리: {dist_decoy:.2f}")

                # 💡 디코이가 없거나 본선이 더 가까울 경우에만 발사
                if not decoys or dist_main < dist_decoy:
                    if not hasattr(self.platform.lo, "decoy_queue") or not self.platform.lo.decoy_queue:
                        new_plan = self.generate_random_decoy_plan()
                        if new_plan:
                            self.platform.lo.get_decoy_list = self.generate_random_decoy_plan
                            self.platform.lo.decoy_queue = new_plan
                            msg.insert_message(SysMessage(self.get_name(), "launch_order"))
                            print(f"[{self.get_name()}] 디코이 발사 명령 전달")

                self.platform.mo.change_heading(self.platform.co.get_evasion_heading())

        self.threat_list = []
        return msg


    def int_trans(self):
        if self._cur_state == "Decision":
            self._cur_state = "Wait"
