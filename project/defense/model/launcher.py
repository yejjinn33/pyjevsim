import datetime
import math

from pyjevsim import BehaviorModel, Infinite
from pyjevsim.system_message import SysMessage
from utils.object_db import ObjectDB

from .stationary_decoy import StationaryDecoy
from .self_propelled_decoy import SelfPropelledDecoy
from ..mobject.stationary_decoy_object import StationaryDecoyObject
from ..mobject.self_propelled_decoy_object import SelfPropelledDecoyObject

class Launcher(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)

        self.platform = platform
        
        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Launch", 0)

        self.insert_input_port("order")
        self.launch_flag = False

    def ext_trans(self, port, msg):
        if port == "order":
            print(f"[{self.get_name()}][order_recv]: {datetime.datetime.now()}")
            self._cur_state = "Launch"

    def output(self, msg):
        se = ObjectDB().get_executor()

        while hasattr(self.platform.lo, "decoy_queue") and self.platform.lo.decoy_queue:
            decoy = self.platform.lo.decoy_queue.pop(0)
            idx = len(ObjectDB().decoys)

            print(f"[{self.get_name()}][Launching Decoy {idx}]: {decoy}")

            destroy_t = math.ceil(decoy['lifespan'])

            if decoy["type"] == "stationary":
                sdo = StationaryDecoyObject(self.platform.get_position(), decoy)
                decoy_model = StationaryDecoy(f"[Decoy][{idx}]", sdo)
            elif decoy["type"] == "self_propelled":
                sdo = SelfPropelledDecoyObject(self.platform.get_position(), decoy)
                decoy_model = SelfPropelledDecoy(f"[Decoy][{idx}]", sdo)
            else:
                continue

            ObjectDB().decoys.append((f"[Decoy][{idx}]", sdo))
            ObjectDB().items.append(sdo)
            se.register_entity(decoy_model, 0, destroy_t)


    def int_trans(self):
        if self._cur_state == "Launch":
            self._cur_state = "Wait"