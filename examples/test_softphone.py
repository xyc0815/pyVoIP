import traceback
from pickle import NONE
import sys
import datetime
from enum import Enum
import time
import wave
import os

sys.path.append('c:/Users/svenr/development/speech_poc_git/pyVoIP')

from pyVoIP.VoIP import VoIPPhone, InvalidStateError, CallState
from pyVoIP.Connections import Connection


class InitValues(Enum):
    WORKING_PATH = 'c:/Users/svenr/development/speech_poc_git/'
    RECORDING_PATH = "recording/"
    FILE_NAME = "voip_rec_"


def answer(call):
    print("+++++++++++++++++ test_softphone answer Get a call")
    os.chdir(InitValues.WORKING_PATH.value)
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")

    try:
        print("+++++++++++++++++  Answer the call")
        call.answer()
        time.sleep(0.1)

        # print("+++++++++++++++++  Get Audio from caller and write file")
        # w = wave.open(f'{InitValues.RECORDING_PATH.value}'
        #              f'{InitValues.FILE_NAME.value}'
        #              f'{message_values.get_call_id()}_'
        #              f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.wav', 'wb')
        # w.setnchannels(1)
        # w.setsampwidth(8 // 8)  # 8 Bit = 1 Byte
        # w.setframerate(8000)

        while call.state == CallState.ANSWERED:
            time.sleep(0.1)
        # w.close()

        print("+++++++++++++++++  End Call hangup and write RabbitMQ")
        call.hangup()
        print("+++++++++++++++++ End of Call")
    except InvalidStateError:
        print("test_softphone Exception InvalidStateError")
        pass
    except Exception as ex:
        print(f"test_softphone Exception and close Call {ex}")
        traceback.print_stack()
        call.hangup()


if __name__ == '__main__':
    server = Connection('server.net', 5060)
    client = Connection('192.168.188.68', 5060)
    proxy = Connection('proxy.server.net', 5060)

    phone = VoIPPhone(server, "user", "passwd", client, proxy, callCallback=answer, rtpPortLow=7079,
                      rtpPortHigh=7096, behind_nat=True)
    phone.start()
    input('\n************************************\nPress enter to disable the phone'
          '\n************************************\n')
    print('\n************************************\nUser pressed enter for stop\n************************************\n')
    phone.stop()
