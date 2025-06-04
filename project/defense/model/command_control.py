import platform
from pyjevsim import BehaviorModel, Infinite
import datetime

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

    def ext_trans(self,port, msg):
        if port == "threat_list":
            print(f"{self.get_name()}[threat_list]: {datetime.datetime.now()}")
            self.threat_list = msg.retrieve()[0]
            self._cur_state = "Decision"

    def output(self, msg):
        for target in self.threat_list:
            if self.platform.co.threat_evaluation(self.platform.mo, target):
                 # 전략 설정 (딱 한 번만 설정됨)
                if not hasattr(self.platform.lo, "strategy_set"):
                    # type -> 고정식(stationary), 자항식(self_propelled)
                    # lifespan : 기만기가 몇초 유지 = 수명
                    # elevation : 발사 각도 (수직 기준)
                    # azimuth : 방위각 (수평 기준) 어느방향으로 쏠지 결정
                    # speed : 발사 속도 [속도가 크면 : 멀리 / 작으면 가까운 거리]
                    # 자항식에만 존재 heading : 자율이동방향(진행방향) / xy_speed : 자율 추진 속도
                    # 1. 전략 리스트 정의
                    decoy_plan = [
                        {"type": "stationary", "lifespan": 10, "elevation": 0, "azimuth": 0, "speed": 10},
                        {"type": "stationary", "lifespan": 10, "elevation": 0, "azimuth": 90, "speed": 10},
                        {"type": "stationary", "lifespan": 10, "elevation": 0, "azimuth": 180, "speed": 10},
                        {"type": "self_propelled", "lifespan": 15, "elevation": 10, "azimuth": 0, "speed": 20, "heading": 0,   "xy_speed": 15},
                        {"type": "self_propelled", "lifespan": 15, "elevation": 10, "azimuth": 270, "speed": 20, "heading": 270, "xy_speed": 15},
                    ]
                    # 2. 강제로 get_decoy_list 함수 오버라이드 (우회 저장)
                    self.platform.lo.get_decoy_list = lambda: decoy_plan

                    # 3. 전략 설정 완료 표시
                    self.platform.lo.strategy_set = True
                
                # send order
                message = SysMessage(self.get_name(), "launch_order")
                msg.insert_message(message)
                # change heading
                self.platform.mo.change_heading(self.platform.co.get_evasion_heading())
        
        self.threat_list = []
        return msg
        
    def int_trans(self):
        if self._cur_state == "Decision":
            self._cur_state = "Wait"