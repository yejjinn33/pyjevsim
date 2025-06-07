import platform
from pyjevsim import BehaviorModel, Infinite
import datetime
from defense.mobject.manuever_object import ManueverObject
from defense.mobject.stationary_decoy_object import StationaryDecoyObject
from defense.mobject.self_propelled_decoy_object import SelfPropelledDecoyObject
from pyjevsim.system_message import SysMessage

class TorpedoCommandControl(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)
        
        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Decision", 0)

        self.insert_input_port("threat_list")
        self.insert_output_port("target")
        self.threat_list = []

        # ✅ 본선을 기억하는 변수
        self.last_seen_manuever = None


    #외부 입력(기만기, 적 탐지 등)에 따라 torpedo의 상태를 바꾸는 함수
    def ext_trans(self,port, msg):
        print("[DEBUG] ext_trans called:", port)  # 추가
        if port == "threat_list":
            print(f"{self.get_name()}[threat_list]: {datetime.datetime.now()}")
            self.threat_list = msg.retrieve()[0]
            self._cur_state = "Decision"

    #torpedo가 다음 행동을 결정할 때 호출됨 (예: 추적 방향, 속도 등)
    def output(self, msg):
        target = None
        target_type = None


        # 우선순위: 본선(Manuever) < 자항식 < 고정식
        priority = {
            "ManueverObject": 0,
            "SelfPropelledDecoyObject": 1,
            "StationaryDecoyObject": 2
        }
        # 우선 본선을 따로 추출
        manuevers = [t for t in self.threat_list if t.__class__.__name__ == "ManueverObject"]
        
        # 본선이 감지됐을 경우 → 추적 우선순위로 처리
        if manuevers:
            self.last_seen_manuever = manuevers[0]
            print("[DEBUG] 본선 감지 → 우선 추적 대상 설정")
            candidate = self.platform.co.get_target(self.platform.mo, self.last_seen_manuever)
            if candidate:
                target = candidate
                target_type = "ManueverObject"
        # 감지된 본선이 없다면 이전 본선 기억으로 추적
        elif self.last_seen_manuever:
            print("[DEBUG] 본선이 감지되지 않음 → 이전 본선 추적 유지")
            candidate = self.platform.co.get_target(self.platform.mo, self.last_seen_manuever)
            if candidate:
                target = candidate
                target_type = "ManueverObject"
        else:
            # 마지막 수단으로 나머지 객체 중 우선순위 높은 것 추적
            sorted_threats = sorted(
                self.threat_list,
                key=lambda t: priority.get(t.__class__.__name__, 99)
            )

            for t in sorted_threats:
                print("[DEBUG] threat_list contains:", t.__class__.__name__, t)
                candidate = self.platform.co.get_target(self.platform.mo, t)
                print("[DEBUG] get_target() 결과:", candidate)
                if candidate:
                    target = candidate
                    target_type = t.__class__.__name__
                    break


        # 실제 선택된 추적 대상 로그
        if target:
            if target_type == "StationaryDecoyObject":
                print("[DEBUG] 실제 추적 대상: 고정식 기만기")
            elif target_type == "SelfPropelledDecoyObject":
                print("[DEBUG] 실제 추적 대상: 자항식 기만기")
            else:
                print("[DEBUG] 실제 추적 대상: 본선")

            message = SysMessage(self.get_name(), "target")
            message.insert(target)
            msg.insert_message(message)
        
                
        # house keeping
        self.threat_list = []
        self.platform.co.reset_target()
        return msg

    #내부 상태 업데이트용 (예: countdown 끝나면 동작 바꿈)    
    def int_trans(self):
        if self._cur_state == "Decision":
            self._cur_state = "Wait"