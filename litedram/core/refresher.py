from litex.gen import *
from litex.gen.genlib.misc import timeline, WaitTimer

from litedram.core.multiplexer import *


class Refresher(Module):
    def __init__(self, a, ba, tRP, tREFI, tRFC, enable):
        self.req = Signal()
        self.ack = Signal()  # 1st command 1 cycle after assertion of ack
        self.cmd = cmd = Record(cmd_request_layout(a, ba))

        # # #

        # Refresh sequence generator:
        # PRECHARGE ALL --(tRP)--> AUTO REFRESH --(tRFC)--> done
        seq_start = Signal()
        seq_done = Signal()
        self.sync += [
            cmd.a.eq(2**10),
            cmd.ba.eq(0),
            cmd.cas.eq(0),
            cmd.ras.eq(0),
            cmd.we.eq(0),
            seq_done.eq(0)
        ]
        self.sync += timeline(seq_start, [
            (1, [
                cmd.ras.eq(1),
                cmd.we.eq(1)
            ]),
            (1+tRP, [
                cmd.cas.eq(1),
                cmd.ras.eq(1)
            ]),
            (1+tRP+tRFC, [
                seq_done.eq(1)
            ])
        ])

        # Periodic refresh counter
        self.submodules.timer = WaitTimer(tREFI)
        self.comb += self.timer.wait.eq(enable & ~self.timer.done)

        # Control FSM
        self.submodules.fsm = fsm = FSM()
        fsm.act("IDLE",
            If(self.timer.done,
                NextState("WAIT_GRANT")
            )
        )
        fsm.act("WAIT_GRANT",
            self.req.eq(1),
            If(self.ack,
                seq_start.eq(1),
                NextState("WAIT_SEQ")
            )
        )
        fsm.act("WAIT_SEQ",
            self.req.eq(1),
            If(seq_done,
                NextState("IDLE")
            )
        )