import traceback
from enum import Enum, IntEnum
from threading import Timer, Lock
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING
import inspect
import pyVoIP
import hashlib
import socket
import netaddr
import random
import time
import uuid
import select
import re

if TYPE_CHECKING:
    from pyVoIP import RTP


__all__ = [
            'Counter', 'InvalidAccountInfoError', 'SIPClient', 'SIPMessage',
            'SIPMessageType', 'SIPParseError', 'SIPStatus'
          ]


debug = pyVoIP.debug


class InvalidAccountInfoError(Exception):
    pass


class SIPParseError(Exception):
    pass


class Counter:

    def __init__(self, start: int = 1):
        self.x = start

    def count(self) -> int:
        x = self.x
        self.x += 1
        return x

    def next(self) -> int:
        return self.count()

    def current(self) -> int:
        return self.x


class SIPStatus(Enum):

    def __new__(cls, value: int, phrase: str = '', description: str = ''):
        obj = object.__new__(cls)
        obj._value_ = value

        obj.phrase = phrase
        obj.description = description
        return obj

    def __int__(self) -> int:
        return self._value_

    def __str__(self) -> str:
        return f"{self._value_} {self.phrase}"

    @property
    def phrase(self) -> str:
        return self._phrase

    @phrase.setter
    def phrase(self, value: str) -> None:
        self._phrase = value

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value

    # Informational
    TRYING = (
                100,
                'Trying',
                'Extended search being performed, may take a significant time'
             )
    RINGING = (
                180,
                'Ringing',
                'Destination user agent received INVITE, ' +
                'and is alerting user of call'
              )
    FORWARDED = 181, 'Call is Being Forwarded'
    QUEUED = 182, 'Queued'
    SESSION_PROGRESS = 183, 'Session Progress'
    TERMINATED = 199, 'Early Dialog Terminated'

    # Success
    OK = 200, 'OK', 'Request successful'
    ACCEPTED = (
                202,
                'Accepted',
                'Request accepted, processing continues (Deprecated.)'
               )
    NO_NOTIFICATION = (
                        204,
                        'No Notification',
                        'Request fulfilled, nothing follows'
                      )

    # Redirection
    MULTIPLE_CHOICES = (
                        300,
                        'Multiple Choices',
                        'Object has several resources -- see URI list'
                       )
    MOVED_PERMANENTLY = (
                            301,
                            'Moved Permanently',
                            'Object moved permanently -- see URI list'
                        )
    MOVED_TEMPORARILY = (
                            302,
                            'Moved Temporarily',
                            'Object moved temporarily -- see URI list'
                        )
    USE_PROXY = (
                    305,
                    'Use Proxy',
                    'You must use proxy specified in Location to ' +
                    'access this resource'
                )
    ALTERNATE_SERVICE = (
                            380,
                            'Alternate Service',
                            'The call failed, but alternatives are ' +
                            'available -- see URI list'
                        )

    # Client Error
    BAD_REQUEST = (
                    400,
                    'Bad Request',
                    'Bad request syntax or unsupported method'
                  )
    UNAUTHORIZED = (
                    401,
                    'Unauthorized',
                    'No permission -- see authorization schemes'
                   )
    PAYMENT_REQUIRED = (
                        402,
                        'Payment Required',
                        'No payment -- see charging schemes'
                       )
    FORBIDDEN = (
                    403,
                    'Forbidden',
                    'Request forbidden -- authorization will not help'
                )
    NOT_FOUND = (
                    404,
                    'Not Found',
                    'Nothing matches the given URI'
                )
    METHOD_NOT_ALLOWED = (
                            405,
                            'Method Not Allowed',
                            'Specified method is invalid for this resource'
                        )
    NOT_ACCEPTABLE = (
                        406,
                        'Not Acceptable',
                        'URI not available in preferred format'
                    )
    PROXY_AUTHENTICATION_REQUIRED = (
                                        407,
                                        'Proxy Authentication Required',
                                        'You must authenticate with this ' +
                                        'proxy before proceeding'
                                    )
    REQUEST_TIMEOUT = (
                        408,
                        'Request Timeout',
                        'Request timed out; try again later'
                      )
    CONFLICT = 409, 'Conflict', 'Request conflict'
    GONE = (
            410,
            'Gone',
            'URI no longer exists and has been permanently removed'
           )
    LENGTH_REQUIRED = (
                        411,
                        'Length Required',
                        'Client must specify Content-Length'
                      )
    CONDITIONAL_REQUEST_FAILED = 412, 'Conditional Request Failed'
    REQUEST_ENTITY_TOO_LARGE = (
                                413,
                                'Request Entity Too Large',
                                'Entity is too large'
                               )
    REQUEST_URI_TOO_LONG = 414, 'Request-URI Too Long', 'URI is too long'
    UNSUPPORTED_MEDIA_TYPE = (
                                415,
                                'Unsupported Media Type',
                                'Entity body in unsupported format'
                             )
    UNSUPPORTED_URI_SCHEME = (
                                416,
                                'Unsupported URI Scheme',
                                'Cannot satisfy request'
                             )
    UNKOWN_RESOURCE_PRIORITY = (
                                417,
                                'Unkown Resource-Priority',
                                'There was a resource-priority option tag, ' +
                                'but no Resource-Priority header'
                               )
    BAD_EXTENSION = (
                        420,
                        'Bad Extension',
                        'Bad SIP Protocol Extension used, not understood ' +
                        'by the server.'
                    )
    EXTENSION_REQUIRED = (
                            421,
                            'Extension Required',
                            'Server requeires a specific extension to be ' +
                            'listed in the Supported header.'
                         )
    SESSION_INTERVAL_TOO_SMALL = 422, 'Session Interval Too Small'
    SESSION_INTERVAL_TOO_BRIEF = 423, 'Session Interval Too Breif'
    BAD_LOCATION_INFORMATION = 424, 'Bad Location Information'
    USE_IDENTITY_HEADER = (
                            428,
                            'Use Identity Header',
                            'The server requires an Identity header, ' +
                            'and one has not been provided.'
                          )
    PROVIDE_REFERRER_IDENTITY = 429, 'Provide Referrer Identity'
    """
    This response is intended for use between proxy devices,
    and should not be seen by an endpoint. If it is seen by one,
    it should be treated as a 400 Bad Request response.
    """
    FLOW_FAILED = (
                    430,
                    'Flow Failed',
                    'A specific flow to a user agent has failed, ' +
                    'although other flows may succeed.'
                  )
    ANONYMITY_DISALLOWED = 433, 'Anonymity Disallowed'
    BAD_IDENTITY_INFO = 436, 'Bad Identity-Info'
    UNSUPPORTED_CERTIFICATE = 437, 'Unsupported Certificate'
    INVALID_IDENTITY_HEADER = 438, 'Invalid Identity Header'
    FIRST_HOP_LACKS_OUTBOUND_SUPPORT = 439, 'First Hop Lacks Outbound Support'
    MAX_BREADTH_EXCEEDED = 440, 'Max-Breadth Exceeded'
    BAD_INFO_PACKAGE = 469, 'Bad Info Package'
    CONSENT_NEEDED = 470, 'Consent Needed'
    TEMPORARILY_UNAVAILABLE = 480, 'Temporarily Unavailable'
    CALL_OR_TRANSACTION_DOESNT_EXIST = 481, 'Call/Transaction Does Not Exist'
    LOOP_DETECTED = 482, 'Loop Detected'
    TOO_MANY_HOPS = 483, 'Too Many Hops'
    ADDRESS_INCOMPLETE = 484, 'Address Incomplete'
    AMBIGUOUS = 485, 'Ambiguous'
    BUSY_HERE = 486, 'Busy Here', 'Callee is busy'
    REQUEST_TERMINATED = 487, 'Request Terminated'
    NOT_ACCEPTABLE_HERE = 488, 'Not Acceptable Here'
    BAD_EVENT = 489, 'Bad Event'
    REQUEST_PENDING = 491, 'Request Pending'
    UNDECIPHERABLE = 493, 'Undecipherable'
    SECURITY_AGREEMENT_REQUIRED = 494, 'Security Agreement Required'

    # Server Errors
    INTERNAL_SERVER_ERROR = (
                                500,
                                'Internal Server Error',
                                'Server got itself in trouble'
                            )
    NOT_IMPLEMENTED = (
                        501,
                        'Not Implemented',
                        'Server does not support this operation'
                      )
    BAD_GATEWAY = (
                    502,
                    'Bad Gateway',
                    'Invalid responses from another server/proxy'
                  )
    SERVICE_UNAVAILABLE = (
                            503,
                            'Service Unavailable',
                            'The server cannot process the request ' +
                            'due to a high load'
                          )
    GATEWAY_TIMEOUT = (
                        504,
                        'Server Timeout',
                        'The server did not receive a timely response'
                      )
    SIP_VERSION_NOT_SUPPORTED = (
                                    505,
                                    'SIP Version Not Supported',
                                    'Cannot fulfill request'
                                )
    MESSAGE_TOO_LONG = 513, 'Message Too Long'
    PUSH_NOTIFICATION_SERVICE_NOT_SUPPORTED = (
                                                555,
                                                'Push Notification Service ' +
                                                'Not Supported'
                                              )
    PRECONDITION_FAILURE = 580, 'Precondition Failure'

    # Global Failure Responses
    BUSY_EVERYWHERE = 600, 'Busy Everywhere'
    DECLINE = 603, 'Decline'
    DOES_NOT_EXIST_ANYWHERE = 604, 'Does Not Exist Anywhere'
    GLOBAL_NOT_ACCEPTABLE = 606, 'Not Acceptable'
    UNWANTED = 607, 'Unwanted'
    REJECTED = 608, 'Rejected'


class SIPMessageType(IntEnum):

    def __new__(cls, value: int):
        obj = int.__new__(cls, value)
        obj._value_ = value
        return obj

    MESSAGE = 1
    RESPONSE = 0


class SIPMessage:

    def __init__(self, data: bytes):
        self.SIPCompatibleVersions = pyVoIP.SIPCompatibleVersions
        self.SIPCompatibleMethods = pyVoIP.SIPCompatibleMethods
        self.heading = b""
        self.type: Optional[SIPMessageType] = None
        self.status = SIPStatus(491)
        self.headers: Dict[str, Any] = {'Via': []}
        self.body: Dict[str, Any] = {}
        self.authentication: Dict[str, str] = {}
        self.raw = data
        self.parse(data)

    def split_address(self, address):
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} with address {address}')
        if address.find("[", 0, 2) == -1:
            debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} IPv4')
            if address.find(":", 0, len(address)) == -1:
                return address, 5060
            else:
                return address.split(':')
        else:
            debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} IPv6')
            index = address.find("]", 0, len(address))
            if index == -1:
                debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} Something wrong')
                return "", ""
            else:
                if address.find(":", index, len(address)) == -1:
                    return address, 5060
                else:
                    new_ip, port = address.rsplit(':', 1)
                    return new_ip.strip('[]'), port

    def summary(self) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        data = ""
        if self.type == SIPMessageType.RESPONSE:
            data += f"Status: {int(self.status)} {self.status.phrase}\n\n"
        else:
            data += f"Method: {self.method}\n\n"
        data += "Headers:\n"
        for x in self.headers:
            data += f"{x}: {self.headers[x]}\n"
        data += "\n"
        data += "Body:\n"
        for x in self.body:
            data += f"{x}: {self.body[x]}\n"

        return data

    def parse(self, data: bytes) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        try:
            headers, body = data.split(b'\r\n\r\n')
        except ValueError as ve:
            debug(f'Error unpacking data, only using header: {ve}')
            headers = data.split(b'\r\n\r\n')[0]

        headers_raw = headers.split(b'\r\n')
        heading = headers_raw.pop(0)
        check = str(heading.split(b" ")[0], 'utf8')

        if check in self.SIPCompatibleVersions:
            self.type = SIPMessageType.RESPONSE
            self.parse_sip_response(data)
        elif check in self.SIPCompatibleMethods:
            self.type = SIPMessageType.MESSAGE
            self.parse_sip_message(data)
        else:
            raise SIPParseError("Unable to decipher SIP request: " +
                                str(heading, 'utf8'))

    def parse_header(self, header: str, data: str) -> None:
        if header == "Via":
            for d in data:
                info = re.split(" |;", d)
                _type = info[0]  # SIP Method
                # Tuple: address, port only for IP4 strait
                # Tuple: [2001:171b:c9b7:4781:e8e2:5043:19e9:cc02]:55960 for IP6
                debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} _address {info[1]}')
                _ip, _port = self.split_address(info[1])
                # debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} splitted _ip {_ip} _port {_port}')
                # if no port is provided in via header assume default port
                # needs to be str. check response build for better str creation
                # Sometime the port comes in via in the rport element
                _via = {'type': _type, 'address': (_ip, _port)}
                for x in info[2:]:  # Sets branch, maddr, ttl, received, and rport if defined as per RFC 3261 20.7
                    if '=' in x:
                        _via[x.split('=')[0]] = x.split('=')[1]
                    else:
                        _via[x] = None
                self.headers['Via'].append(_via)
        elif header == "From" or header == "To":
            info = data.split(';tag=')
            tag = ''
            if len(info) >= 2:
                tag = info[1]
            raw = info[0]
            # For some header from / to are only sip:xxxx@xxxxxx not <sip:xxxxxxx@xxxxxxxxx>
            # so changed raw.split to the regex version re.split
            # fix issue 41 part 1
            contact = re.split(r"<?sip:", raw)
            contact[0] = contact[0].strip('"').strip("'")
            address = contact[1].strip('>')
            if len(address.split('@')) == 2:
                number = address.split('@')[0]
                host = address.split('@')[1]
            else:
                number = None
                host = address

            self.headers[header] = {
                                    'raw': raw, 'tag': tag, 'address': address,
                                    'number': number, 'caller': contact[0],
                                    'host': host
                                   }
        elif header == "CSeq":
            self.headers[header] = {
                                    'check': data.split(" ")[0],
                                    'method': data.split(" ")[1]
                                   }
        elif header == "Allow" or header == "Supported":
            self.headers[header] = data.split(", ")
        elif header == "Content-Length":
            self.headers[header] = int(data)
        elif header == "WWW-Authenticate" or header == "Authorization":
            data = data.replace("Digest", "")
            #  fix issue 41 part 2
            #  add blank to avoid the split of qop="auth,auth-int"
            info = data.split(", ")
            header_data = {}
            for x in info:
                x = x.strip()
                header_data[x.split('=')[0]] = x.split('=')[1].strip('"')
            self.headers[header] = header_data
            self.authentication = header_data
        else:
            self.headers[header] = data

    def parse_body(self, header: str, data: str) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} start')
        if 'Content-Encoding' in self.headers:
            raise SIPParseError("Unable to parse encoded content.")
        if self.headers['Content-Type'] == 'application/sdp':
            # Referenced RFC 4566 July 2006
            if header == "v":
                # SDP 5.1 Version
                self.body[header] = int(data)
            elif header == "o":
                # SDP 5.2 Origin
                # o=<username> <sess-id> <sess-version> <nettype> <addrtype> <unicast-address> # noqa: E501
                d = data.split(' ')
                self.body[header] = {
                                        'username': d[0], 'id': d[1],
                                        'version': d[2],
                                        'network_type': d[3],
                                        'address_type': d[4],
                                        'address': d[5]
                                    }
            elif header == "s":
                # SDP 5.3 Session Name
                # s=<session name>
                self.body[header] = data
            elif header == "i":
                # SDP 5.4 Session Information
                # i=<session-description>
                self.body[header] = data
            elif header == "u":
                # SDP 5.5 URI
                # u=<uri>
                self.body[header] = data
            elif header == "e" or header == "p":
                # SDP 5.6 Email Address and Phone Number of person
                # responsible for the conference
                # e=<email-address>
                # p=<phone-number>
                self.body[header] = data
            elif header == "c":
                # SDP 5.7 Connection Data
                # c=<nettype> <addrtype> <connection-address>
                if 'c' not in self.body:
                    self.body['c'] = []
                d = data.split(' ')
                # TTL Data and Multicast addresses may be specified.
                # For IPv4 its listed as addr/ttl/number of addresses.
                # c=IN IP4 224.2.1.1/127/3 means:
                # c=IN IP4 224.2.1.1/127
                # c=IN IP4 224.2.1.2/127
                # c=IN IP4 224.2.1.3/127
                # With the TTL being 127.
                # IPv6 does not support time to live so you will only see a '/'
                # for multicast addresses.
                if '/' in d[2]:
                    if d[1] == "IP6":
                        self.body[header].append({
                            'network_type': d[0],
                            'address_type': d[1],
                            'address': d[2].split('/')[0],
                            'ttl': None,
                            'address_count': int(d[2].split('/')[1])
                        })
                    else:
                        address_data = d[2].split('/')
                        if len(address_data) == 2:
                            self.body[header].append({
                                'network_type': d[0],
                                'address_type': d[1],
                                'address': address_data[0],
                                'ttl': int(address_data[1]),
                                'address_count': 1
                            })
                        else:
                            self.body[header].append({
                                'network_type': d[0],
                                'address_type': d[1],
                                'address': address_data[0],
                                'ttl': int(address_data[1]),
                                'address_count': int(address_data[2])
                            })
                else:
                    self.body[header].append({
                                                'network_type': d[0],
                                                'address_type': d[1],
                                                'address': d[2],
                                                'ttl': None, 'address_count': 1
                                             })
            elif header == "b":
                # SDP 5.8 Bandwidth
                # b=<bwtype>:<bandwidth>
                # A bwtype of CT means Conference Total between all medias
                # and all devices in the conference.
                # A bwtype of AS means Applicaton Specific total for this
                # media and this device.
                # The bandwidth is given in kilobits per second.
                # As this was written in 2006, this could be Kibibits.
                # TODO: Implement Bandwidth restrictions
                d = data.split(':')
                self.body[header] = {'type': d[0], 'bandwidth': d[1]}
            elif header == "t":
                # SDP 5.9 Timing
                # t=<start-time> <stop-time>
                d = data.split(' ')
                self.body[header] = {'start': d[0], 'stop': d[1]}
            elif header == "r":
                # SDP 5.10 Repeat Times
                # r=<repeat interval> <active duration> <offsets from start-time> # noqa: E501
                d = data.split(' ')
                self.body[header] = {
                                        'repeat': d[0], 'duration': d[1],
                                        'offset1': d[2], 'offset2': d[3]
                                    }
            elif header == "z":
                # SDP 5.11 Time Zones
                # z=<adjustment time> <offset> <adjustment time> <offset> ....
                # Used for change in timezones such as day light savings time.
                d = data.split()
                amount = len(d) / 2
                self.body[header] = {}
                for x in range(int(amount)):
                    self.body[header]['adjustment-time' + str(x)] = d[x * 2]
                    self.body[header]['offset' + str(x)] = d[x * 2 + 1]
            elif header == "k":
                # SDP 5.12 Encryption Keys
                # k=<method>
                # k=<method>:<encryption key>
                if ':' in data:
                    d = data.split(':')
                    self.body[header] = {'method': d[0], 'key': d[1]}
                else:
                    self.body[header] = {'method': d}
            elif header == "m":
                # SDP 5.14 Media Descriptions
                # m=<media> <port>/<number of ports> <proto> <fmt> ...
                # <port> should be even, and <port>+1 should be the RTCP port.
                # <number of ports> should coinside with number of
                # addresses in SDP 5.7 c=
                if 'm' not in self.body:
                    self.body['m'] = []
                d = data.split(' ')

                if '/' in d[1]:
                    ports_raw = d[1].split('/')
                    port = ports_raw[0]
                    count = int(ports_raw[1])
                else:
                    port = d[1]
                    count = 1
                methods = d[3:]

                self.body['m'].append({
                    'type': d[0], 'port': int(port),
                    'port_count': count,
                    'protocol': pyVoIP.RTP.RTPProtocol(d[2]),
                    'methods': methods, 'attributes': {}
                })
                for x in self.body['m'][-1]['methods']:
                    self.body['m'][-1]['attributes'][x] = {}
            elif header == "a":
                # SDP 5.13 Attributes & 6.0 SDP Attributes
                # a=<attribute>
                # a=<attribute>:<value>

                if "a" not in self.body:
                    self.body['a'] = {}

                if ':' in data:
                    d = data.split(':')
                    attribute = d[0]
                    value = d[1]
                else:
                    attribute = data
                    value = None

                if value is not None:
                    if attribute == "rtpmap":
                        # a=rtpmap:<payload type> <encoding name>/<clock rate> [/<encoding parameters>] # noqa: E501
                        v = re.split(" |/", value)
                        if 'm' in self.body:
                            for t in self.body['m']:
                                if v[0] in t['methods']:
                                    index = int(self.body['m'].index(t))
                                    break
                            if len(v) == 4:
                                encoding = v[3]
                            else:
                                encoding = None

                            self.body['m'][index]['attributes'][v[0]]['rtpmap'] = {
                                'id': v[0], 'name': v[1], 'frequency': v[2],
                                'encoding': encoding
                            }
                    elif attribute == "fmtp":
                        # a=fmtp:<format> <format specific parameters>
                        d = value.split(' ')
                        if 'm' in self.body:
                            for t in self.body['m']:
                                if d[0] in t['methods']:
                                    index = int(self.body['m'].index(t))
                                    break

                            self.body['m'][index]['attributes'][d[0]]['fmtp'] = {
                                'id': d[0], 'settings': d[1:]}
                    else:
                        self.body['a'][attribute] = value
                else:
                    if (attribute == "recvonly" or attribute == "sendrecv" or
                       attribute == "sendonly" or attribute == "inactive"):
                        self.body['a']['transmit_type'] = pyVoIP.RTP.TransmitType(attribute)  # noqa: E501
            else:
                self.body[header] = data

        else:
            self.body[header] = data

    @staticmethod
    def parse_raw_header(headers_raw: List[bytes],
                         handle: Callable[[str, str], None]) -> None:
        debug(f'SIPMessage.parseRawHeader start (staticmethod)')
        headers: Dict[str, Any] = {'Via': []}
        # Only use first occurance of VIA header field;
        # got second VIA from Kamailio running in DOCKER
        # According to RFC 3261 these messages should be
        # discarded in a response
        for x in headers_raw:
            i = str(x, 'utf8').split(': ')
            if i[0] == 'Via':
                headers['Via'].append(i[1])
            if i[0] not in headers.keys():
                headers[i[0]] = i[1]

        for key, val in headers.items():
            handle(key, val)

    @staticmethod
    def parse_raw_body(body: bytes,
                       handle: Callable[[str, str], None]) -> None:
        debug(f"SIPMessage.parseRawBody start (staticmethode)")
        if len(body) > 0:
            body_raw = body.split(b'\r\n')
            # create a unique list of the body to avoid duplicate c elements. See also ToDo VoIP gen_ms
            body_raw = list(set(body_raw))
            for x in body_raw:
                i = str(x, 'utf8').split('=')
                if i != ['']:
                    handle(i[0], i[1])

    def parse_sip_response(self, data: bytes) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        headers, body = data.split(b'\r\n\r\n')

        headers_raw = headers.split(b'\r\n')
        self.heading = headers_raw.pop(0)
        self.version = str(self.heading.split(b" ")[0], 'utf8')
        if self.version not in self.SIPCompatibleVersions:
            raise SIPParseError(f"SIP Version {self.version} not compatible.")

        self.status = SIPStatus(int(self.heading.split(b" ")[1]))

        self.parse_raw_header(headers_raw, self.parse_header)
        
        self.parse_raw_body(body, self.parse_body)

    def parse_sip_message(self, data: bytes) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        headers, body = data.split(b'\r\n\r\n')

        headers_raw = headers.split(b'\r\n')
        self.heading = headers_raw.pop(0)
        self.version = str(self.heading.split(b" ")[2], 'utf8')
        if self.version not in self.SIPCompatibleVersions:
            raise SIPParseError(f"SIP Version {self.version} not compatible.")

        self.method = str(self.heading.split(b" ")[0], 'utf8')

        self.parse_raw_header(headers_raw, self.parse_header)

        self.parse_raw_body(body, self.parse_body)


class SIPClient:

    def __init__(self, server: str, port: int, username: str, password: str,
                 myIP="0.0.0.0", proxy=None, myPort=5060,
                 callCallback: Optional[Callable[[SIPMessage],
                                                 None]] = None):
        self.NSD = False
        self.use_keep_alive = False
        self.server = server
        self.port = port
        self.myIP = myIP
        self.my_public_ip = None
        self.proxy = proxy
        self.username = username
        self.password = password

        self.callCallback = callCallback

        self.tags: List[str] = []
        self.tagLibrary = {'register': self.genTag()}

        self.myPort = myPort
        self.my_public_port = None

        self.default_expires = 120
        self.register_timeout = 30

        self.inviteCounter = Counter()
        self.registerCounter = Counter()
        self.subscribeCounter = Counter()
        self.byeCounter = Counter()
        self.callID = Counter()
        self.sessID = Counter()

        self.urnUUID = self.gen_urn_uuid()

        self.registerThread: Optional[Timer] = None
        self.recvLock = Lock()

    def send_message(self, message: str) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} '
              f'--> message sever {(self.proxy if self.proxy else self.server)} port {self.port}'
              f'\n----\n{message}\n----\n')
        self.out.sendto(message.encode('utf8'), ((self.proxy if self.proxy else self.server), self.port))

    def get_my_ip(self) -> str:
        return self.my_public_ip if self.my_public_ip else self.myIP

    def get_my_port(self) -> str:
        return self.my_public_port if self.my_public_port else self.myPort

    def recv(self) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        while self.NSD:
            self.recvLock.acquire()
            self.s.setblocking(False)
            try:
                raw = self.s.recv(8192)
                debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message recv\n----\n{raw}\n----\n")
                if raw != b'\x00\x00\x00\x00':
                    try:
                        message = SIPMessage(raw)
                        self.parse_message(message)
                    except Exception as ex:
                        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} Error on header parsing: {ex}'
                              f'\n{traceback.format_exc()}')
            except BlockingIOError:
                self.s.setblocking(True)
                self.recvLock.release()
                time.sleep(0.01)
                continue
            except SIPParseError as e:
                if "SIP Version" in str(e):
                    request = self.gen_sip_version_not_supported(message)
                    self.send_message(request)
                else:
                    debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} SIPParseError in SIP.recv: "
                          f"{type(e)}, {e}")
            except Exception as e:
                if pyVoIP.DEBUG:
                    debug(f"\n------------------------\n{self.__class__.__name__}.{inspect.stack()[0][3]} "
                          f"Exception in SIP.recv: {type(e)}, {e}\n------------------------\n")
                    self.s.setblocking(True)
                    self.recvLock.release()
                    raise
            self.s.setblocking(True)
            self.recvLock.release()
            debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} End")

    def parse_message(self, message: SIPMessage) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        if message.type != SIPMessageType.MESSAGE:
            if message.status == SIPStatus.OK:
                if self.callCallback is not None:
                    self.callCallback(message)
            elif message.status == SIPStatus.NOT_FOUND:
                if self.callCallback is not None:
                    self.callCallback(message)
            elif message.status == SIPStatus.SERVICE_UNAVAILABLE:
                if self.callCallback is not None:
                    self.callCallback(message)
            elif (message.status == SIPStatus.TRYING or
                  message.status == SIPStatus.RINGING):
                pass
            else:
                debug("TODO: Add 500 Error on Receiving SIP Response:\r\n" +
                      message.summary(), "TODO: Add 500 Error on Receiving " +
                      "SIP Response")
            self.s.setblocking(True)
            return
        elif message.method == "INVITE":
            if self.callCallback is None:
                request = self.gen_busy(message)
                self.send_message(request)
            else:
                self.callCallback(message)
        elif message.method == "BYE":
            # TODO: If callCallback is None, the call doesn't exist, 481
            self.callCallback(message)  # type: ignore
            response = self.gen_ok(message)
            # I don't need this, when using an external server
            try:
                (
                    _sender_adress,
                    _sender_port
                ) = message.headers['Via'][0]['address']
                self.send_message(response)
            except Exception as ex:
                debug('BYE Answer failed falling back to server as target')
                self.send_message(response)
        elif message.method == "ACK":
            return
        elif message.method == "CANCEL":
            # TODO: If callCallback is None, the call doesn't exist, 481
            self.callCallback(message)  # type: ignore
            response = self.gen_ok(message)
            self.send_message(response)
        elif message.method == "NOTIFY":
            self.callCallback(message)
            response = self.gen_notify(message)
            self.send_message(response)
        else:
            debug("TODO: Add 400 Error on non processable request")

    def start(self) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start '
              f'IP {self.myIP} Port {self.myPort}')
        if self.NSD:
            raise RuntimeError("Attempted to start already started SIPClient")
        self.NSD = True
        self.s = socket.socket((socket.AF_INET if netaddr.valid_ipv4(self.myIP) else socket.AF_INET6),
                               socket.SOCK_DGRAM)
        self.s.bind((self.myIP, self.myPort))
        self.out = self.s
        self.register()
        t = Timer(1, self.recv)
        t.name = "SIP Recieve"
        t.start()

    def stop(self) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        self.NSD = False
        self.use_keep_alive = False
        if self.registerThread:
            # Only run if registerThread exists
            self.registerThread.cancel()
            self.deregister()
        self._close_sockets()

    def _close_sockets(self) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        if self.s:
            self.s.close()
        if self.out:
            self.out.close()

    def gen_call_id(self) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        hash = hashlib.sha256(str(self.callID.next()).encode('utf8'))
        hhash = hash.hexdigest()
        return f"{hhash[0:32]}@{self.myIP}:{self.myPort}"

    def gen_last_call_id(self) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        hash = hashlib.sha256(str(self.callID.current() - 1).encode('utf8'))
        hhash = hash.hexdigest()
        return f"{hhash[0:32]}@{self.myIP}:{self.myPort}"

    def gen_tag(self) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start '
              f'NSD {self.NSD}')
        while True:
            rand = str(random.randint(1, 4294967296)).encode('utf8')
            tag = hashlib.md5(rand).hexdigest()[0:8]
            if tag not in self.tags:
                self.tags.append(tag)
                return tag
        return ""

    def gen_sip_version_not_supported(self, request: SIPMessage) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        response = "SIP/2.0 505 SIP Version Not Supported\r\n"
        response += self._gen_response_via_header(request)
        response += f"From: {request.headers['From']['raw']};tag=" + \
                    f"{request.headers['From']['tag']}\r\n"
        response += f"To: {request.headers['To']['raw']};tag=" + \
                    f"{self.gen_tag()}\r\n"
        response += f"Call-ID: {request.headers['Call-ID']}\r\n"
        response += f"CSeq: {request.headers['CSeq']['check']} " + \
                    f"{request.headers['CSeq']['method']}\r\n"
        response += f"Contact: {request.headers['Contact']}\r\n"
        response += f"User-Agent: pyVoIP {pyVoIP.__version__}\r\n"
        response += "Warning: 399 GS \"Unable to accept call\"\r\n"
        response += f"Allow: {(', '.join(pyVoIP.SIPCompatibleMethods))}\r\n"
        response += "Content-Length: 0\r\n\r\n"

        return response

    def gen_authorization(self, request):
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        realm = request.authentication['realm']
        HA1 = self.username + ':' + realm + ':' + self.password
        HA1 = hashlib.md5(HA1.encode('utf8')).hexdigest()
        HA2 = "" + request.headers['CSeq']['method'] + ':sip:' + \
              self.server + ';transport=UDP'
        HA2 = hashlib.md5(HA2.encode('utf8')).hexdigest()
        nonce = request.authentication['nonce']
        response = (HA1 + ':' + nonce + ':' + HA2).encode('utf8')
        response = hashlib.md5(response).hexdigest().encode('utf8')

        return response

    def gen_branch(self, length=32) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        """
        Generate unique branch id according to
        https://datatracker.ietf.org/doc/html/rfc3261#section-8.1.1.7
        """
        branchid = uuid.uuid4().hex[:length - 7]
        return f"z9hG4bK{branchid}"

    def gen_urn_uuid(self):
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        '''
        Generate client instance specific urn:uuid
        '''
        return str(uuid.uuid4()).upper()

    def gen_first_response(self, deregister=False) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        regRequest = f'REGISTER sip:{self.server} SIP/2.0\r\n'
        regRequest += f'Via: SIP/2.0/UDP {self.myIP}:{self.myPort};' + \
                      f'branch={self.gen_branch()};rport\r\n'
        regRequest += f'From: "{self.username}" ' + \
                      f'<sip:{self.username}@{self.server}>;tag=' + \
                      f'{self.tagLibrary["register"]}\r\n'
        regRequest += f'To: "{self.username}" ' + \
                      f'<sip:{self.username}@{self.server}>\r\n'
        regRequest += f'Call-ID: {self.gen_call_id()}\r\n'
        regRequest += f'CSeq: {self.registerCounter.next()} REGISTER\r\n'
        regRequest += 'Contact: ' + \
                      f'<sip:{self.get_my_ip()}:{self.get_my_port()};' + \
                      'transport=UDP>;+sip.instance=' + \
                      f'"<urn:uuid:{self.urnUUID}>"\r\n'
        regRequest += f'Allow: {(", ".join(pyVoIP.SIPCompatibleMethods))}\r\n'
        regRequest += 'Max-Forwards: 70\r\n'
        regRequest += 'Allow-Events: org.3gpp.nwinitdereg\r\n'
        regRequest += f'User-Agent: pyVoIP {pyVoIP.__version__}\r\n'
        # Supported: 100rel, replaces, from-change, gruu
        regRequest += 'Expires: ' + \
                      f'{self.default_expires if not deregister else 0}\r\n'
        regRequest += 'Content-Length: 0'
        regRequest += '\r\n\r\n'

        return regRequest

    def gen_subscribe(self, response: SIPMessage) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        subRequest = f'SUBSCRIBE sip:{self.username}@{self.server} SIP/2.0\r\n'
        subRequest += f'Via: SIP/2.0/UDP {self.myIP}:{self.myPort};' + \
                      f'branch={self.gen_branch()};rport\r\n'
        subRequest += f'From: "{self.username}" ' + \
                      f'<sip:{self.username}@{self.server}>;tag=' + \
                      f'{self.gen_tag()}\r\n'
        subRequest += f'To: <sip:{self.username}@{self.server}>\r\n'
        subRequest += f'Call-ID: {response.headers["Call-ID"]}\r\n'
        subRequest += f'CSeq: {self.subscribeCounter.next()} SUBSCRIBE\r\n'
        # TODO: check if transport is needed
        subRequest += 'Contact: ' + \
                      f'<sip:{self.username}@{self.get_my_ip()}:{self.get_my_port()};' + \
                      'transport=UDP>;+sip.instance=' + \
                      f'"<urn:uuid:{self.urnUUID}>"\r\n'
        subRequest += f'Max-Forwards: 70\r\n'
        subRequest += f'User-Agent: pyVoIP {pyVoIP.__version__}\r\n'
        subRequest += f'Expires: {self.default_expires * 2}\r\n'
        subRequest += 'Event: message-summary\r\n'
        subRequest += 'Accept: application/simple-message-summary'
        subRequest += 'Content-Length: 0'
        subRequest += '\r\n\r\n'

        return subRequest

    def gen_register(self, request: SIPMessage, deregister=False) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        response = str(self.gen_authorization(request), 'utf8')
        nonce = request.authentication['nonce']
        realm = request.authentication['realm']

        regRequest = f'REGISTER sip:{self.server} SIP/2.0\r\n'
        regRequest += f'Via: SIP/2.0/UDP {self.myIP}:{self.myPort};branch=' \
                      f'{self.gen_branch()};rport\r\n'
        regRequest += f'From: "{self.username}" ' \
                      f'<sip:{self.username}@{self.server}>;tag=' \
                      f'{self.tagLibrary["register"]}\r\n'
        regRequest += f'To: "{self.username}" ' \
                      f'<sip:{self.username}@{self.server}>\r\n'
        regRequest += f'Call-ID: {self.gen_call_id()}\r\n'
        regRequest += f'CSeq: {self.registerCounter.next()} REGISTER\r\n'
        regRequest += f'Contact: ' \
                      f'<sip:{self.username}@{self.get_my_ip()}:{self.get_my_port()};' \
                      f'transport=UDP>;+sip.instance=' \
                      f'"<urn:uuid:{self.urnUUID}>"\r\n'
        regRequest += f'Allow: {(", ".join(pyVoIP.SIPCompatibleMethods))}\r\n'
        regRequest += 'Max-Forwards: 70\r\n'
        regRequest += 'Allow-Events: org.3gpp.nwinitdereg\r\n'
        regRequest += f'User-Agent: pyVoIP {pyVoIP.__version__}\r\n'
        regRequest += 'Expires: ' + \
                      f'{self.default_expires if not deregister else 0}\r\n'
        regRequest += f'Authorization: Digest username="{self.username}",' + \
                      f'realm="{realm}",nonce="{nonce}",' + \
                      f'uri="sip:{self.server};transport=UDP",' + \
                      f'response="{response}",algorithm=MD5\r\n'
        regRequest += 'Content-Length: 0'
        regRequest += '\r\n\r\n'

        return regRequest

    def gen_busy(self, request: SIPMessage) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        response = "SIP/2.0 486 Busy Here\r\n"
        response += self._gen_response_via_header(request)
        response += f"From: {request.headers['From']['raw']};tag=" + \
                    f"{request.headers['From']['tag']}\r\n"
        response += f"To: {request.headers['To']['raw']};tag=" + \
                    f"{self.gen_tag()}\r\n"
        response += f"Call-ID: {request.headers['Call-ID']}\r\n"
        response += f"CSeq: {request.headers['CSeq']['check']} " + \
                    f"{request.headers['CSeq']['method']}\r\n"
        response += f"Contact: {request.headers['Contact']}\r\n"
        # TODO: Add Supported
        response += f"User-Agent: pyVoIP {pyVoIP.__version__}\r\n"
        response += "Warning: 399 GS \"Unable to accept call\"\r\n"
        response += f"Allow: {(', '.join(pyVoIP.SIPCompatibleMethods))}\r\n"
        response += "Content-Length: 0\r\n\r\n"

        return response

    def gen_ok(self, request: SIPMessage) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        okResponse = "SIP/2.0 200 OK\r\n"
        okResponse += self._gen_response_via_header(request)
        okResponse += f"From: {request.headers['From']['raw']};tag=" + \
                      f"{request.headers['From']['tag']}\r\n"
        okResponse += f"To: {request.headers['To']['raw']};tag=" + \
                      f"{self.gen_tag()}\r\n"
        okResponse += f"Call-ID: {request.headers['Call-ID']}\r\n"
        okResponse += f"CSeq: {request.headers['CSeq']['check']} " + \
                      f"{request.headers['CSeq']['method']}\r\n"
        okResponse += f"User-Agent: pyVoIP {pyVoIP.__version__}\r\n"
        okResponse += f"Allow: {(', '.join(pyVoIP.SIPCompatibleMethods))}\r\n"
        okResponse += "Content-Length: 0\r\n\r\n"

        return okResponse

    def gen_notify(self, request):
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        notify_response = "SIP/2.0 200 OK\r\n"
        notify_response += self._gen_response_via_header(request)
        notify_response += f"To: {request.headers['To']['raw']};tag={request.headers['To']['tag']}\r\n"
        notify_response += f"From: {request.headers['From']['raw']};tag={request.headers['From']['tag']}\r\n"
        notify_response += f"Call-ID: {request.headers['Call-ID']}\r\n"
        notify_response += f"CSeq: {int(request.headers['CSeq']['check'])+1} {request.headers['CSeq']['method']}\r\n"
        notify_response += f"Event: {request.headers['Event']}\r\n"
        notify_response += "Content-Length: 0\r\n\r\n"

        if request.headers['Event'] == "keep-alive":
            self.use_keep_alive = True
        return notify_response

    def gen_ringing(self, request: SIPMessage) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        tag = self.gen_tag()
        regRequest = "SIP/2.0 180 Ringing\r\n"
        regRequest += self._gen_response_via_header(request)
        regRequest += f"From: {request.headers['From']['raw']};tag=" + \
                      f"{request.headers['From']['tag']}\r\n"
        regRequest += f"To: {request.headers['To']['raw']};tag={tag}\r\n"
        regRequest += f"Call-ID: {request.headers['Call-ID']}\r\n"
        regRequest += f"CSeq: {request.headers['CSeq']['check']} " + \
                      f"{request.headers['CSeq']['method']}\r\n"
        regRequest += f"Contact: {request.headers['Contact']}\r\n"
        # TODO: Add Supported
        regRequest += f"User-Agent: pyVoIP {pyVoIP.__version__}\r\n"
        regRequest += f"Allow: {(', '.join(pyVoIP.SIPCompatibleMethods))}\r\n"
        regRequest += "Content-Length: 0\r\n\r\n"

        self.tagLibrary[request.headers['Call-ID']] = tag

        return regRequest

    def gen_answer(self, request: SIPMessage, sess_id: str,
                   ms: Dict[int, Dict[int, 'RTP.PayloadType']],
                   sendtype: 'RTP.TransmitType') -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        # Generate body first for content length
        body = "v=0\r\n"
        # TODO: Check IPv4/IPv6
        body += f"o=pyVoIP {sess_id} {int(sess_id)+2} IN IP4 {self.get_my_ip()}\r\n"
        body += f"s=pyVoIP {pyVoIP.__version__}\r\n"
        # TODO: Check IPv4/IPv6
        body += f"c=IN IP4 {self.get_my_ip()}\r\n"
        body += "t=0 0\r\n"
        for x in ms:
            # TODO: Check AVP mode from request
            body += f"m=audio {x} RTP/AVP"
            for m in ms[x]:
                body += f" {m}"
        body += "\r\n"  # m=audio <port> RTP/AVP <codecs>\r\n
        for x in ms:
            for m in ms[x]:
                body += f"a=rtpmap:{m} {ms[x][m]}/{ms[x][m].rate}\r\n"
                if str(ms[x][m]) == "telephone-event":
                    body += f"a=fmtp:{m} 0-15\r\n"
        body += "a=ptime:20\r\n"
        body += "a=maxptime:150\r\n"
        body += f"a={sendtype}\r\n"

        tag = self.tagLibrary[request.headers['Call-ID']]

        regRequest = "SIP/2.0 200 OK\r\n"
        regRequest += self._gen_response_via_header(request)
        regRequest += f"From: {request.headers['From']['raw']};tag=" + \
                      f"{request.headers['From']['tag']}\r\n"
        regRequest += f"To: {request.headers['To']['raw']};tag={tag}\r\n"
        regRequest += f"Call-ID: {request.headers['Call-ID']}\r\n"
        regRequest += f"CSeq: {request.headers['CSeq']['check']} " + \
                      f"{request.headers['CSeq']['method']}\r\n"
        regRequest += "Contact: " + \
                      f"<sip:{self.username}@{self.get_my_ip()}:{self.get_my_port()}>\r\n"
        # TODO: Add Supported
        regRequest += f"User-Agent: pyVoIP {pyVoIP.__version__}\r\n"
        regRequest += f"Allow: {(', '.join(pyVoIP.SIPCompatibleMethods))}\r\n"
        regRequest += "Content-Type: application/sdp\r\n"
        regRequest += f"Content-Length: {len(body)}\r\n\r\n"
        regRequest += body

        return regRequest

    def gen_invite(self, number: str, sess_id: str,
                   ms: Dict[int, Dict[str, 'RTP.PayloadType']],
                   sendtype: 'RTP.TransmitType', branch: str, call_id: str
                   ) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        # Generate body first for content length
        body = "v=0\r\n"
        # TODO: Check IPv4/IPv6
        body += f"o=pyVoIP {sess_id} {int(sess_id)+2} IN IP4 {self.get_my_port()}\r\n"
        body += f"s=pyVoIP {pyVoIP.__version__}\r\n"
        body += f"c=IN IP4 {self.get_my_ip()}\r\n"  # TODO: Check IPv4/IPv6
        body += "t=0 0\r\n"
        for x in ms:
            # TODO: Check AVP mode from request
            body += f"m=audio {x} RTP/AVP"
            for m in ms[x]:
                body += f" {m}"
        body += "\r\n"  # m=audio <port> RTP/AVP <codecs>\r\n
        for x in ms:
            for m in ms[x]:
                body += f"a=rtpmap:{m} {ms[x][m]}/{ms[x][m].rate}\r\n"
                if str(ms[x][m]) == "telephone-event":
                    body += f"a=fmtp:{m} 0-15\r\n"
        body += "a=ptime:20\r\n"
        body += "a=maxptime:150\r\n"
        body += f"a={sendtype}\r\n"

        tag = self.gen_tag()
        self.tagLibrary[call_id] = tag

        invRequest = f"INVITE sip:{number}@{self.server} SIP/2.0\r\n"
        invRequest += f"Via: SIP/2.0/UDP {self.myIP}:{self.myPort};branch=" + \
                      f"{branch}\r\n"
        invRequest += "Max-Forwards: 70\r\n"
        invRequest += "Contact: " + \
                      f"<sip:{self.username}@{self.get_my_ip()}:{self.get_my_port()}>\r\n"
        invRequest += f"To: <sip:{number}@{self.server}>\r\n"
        invRequest += f"From: <sip:{self.username}@{self.myIP}>;tag={tag}\r\n"
        invRequest += f"Call-ID: {call_id}\r\n"
        invRequest += f"CSeq: {self.inviteCounter.next()} INVITE\r\n"
        invRequest += f"Allow: {(', '.join(pyVoIP.SIPCompatibleMethods))}\r\n"
        invRequest += "Content-Type: application/sdp\r\n"
        invRequest += f"User-Agent: pyVoIP {pyVoIP.__version__}\r\n"
        invRequest += f"Content-Length: {len(body)}\r\n\r\n"
        invRequest += body

        return invRequest

    def gen_bye(self, request: SIPMessage) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        tag = self.tagLibrary[request.headers['Call-ID']]
        c = request.headers['Contact'].strip('<').strip('>')
        byeRequest = f"BYE {c} SIP/2.0\r\n"
        byeRequest += self._gen_response_via_header(request)
        fromH = request.headers['From']['raw']
        toH = request.headers['To']['raw']
        if request.headers['From']['tag'] == tag:
            byeRequest += f"From: {fromH};tag={tag}\r\n"
            if request.headers['To']['tag'] != '':
                to = toH + ';tag=' + request.headers['To']['tag']
            else:
                to = toH
            byeRequest += f"To: {to}\r\n"
        else:
            byeRequest += f"To: {fromH};tag=" + \
                          f"{request.headers['From']['tag']}\r\n"
            byeRequest += f"From: {toH};tag={tag}\r\n"
        byeRequest += f"Call-ID: {request.headers['Call-ID']}\r\n"
        cseq = int(request.headers['CSeq']['check']) + 1
        byeRequest += f"CSeq: {cseq} BYE\r\n"
        byeRequest += "Contact: " + \
                      f"<sip:{self.username}@{self.get_my_ip()}:{self.get_my_port()}>\r\n"
        byeRequest += f"User-Agent: pyVoIP {pyVoIP.__version__}\r\n"
        byeRequest += f"Allow: {(', '.join(pyVoIP.SIPCompatibleMethods))}\r\n"
        byeRequest += "Content-Length: 0\r\n\r\n"

        return byeRequest

    def gen_ack(self, request: SIPMessage) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        tag = self.tagLibrary[request.headers['Call-ID']]
        t = request.headers['To']['raw'].strip('<').strip('>')
        ackMessage = f"ACK {t} SIP/2.0\r\n"
        ackMessage += self._gen_response_via_header(request)
        ackMessage += "Max-Forwards: 70\r\n"
        ackMessage += f"To: {request.headers['To']['raw']};tag=" + \
                      f"{self.gen_tag()}\r\n"
        ackMessage += f"From: {request.headers['From']['raw']};tag={tag}\r\n"
        ackMessage += f"Call-ID: {request.headers['Call-ID']}\r\n"
        ackMessage += f"CSeq: {request.headers['CSeq']['check']} ACK\r\n"
        ackMessage += f"User-Agent: pyVoIP {pyVoIP.__version__}\r\n"
        ackMessage += "Content-Length: 0\r\n\r\n"

        return ackMessage

    def _gen_response_via_header(self, request: SIPMessage) -> str:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        via = ''
        for h_via in request.headers['Via']:
            address = h_via["address"][0]
            if netaddr.valid_ipv6(address):
                address = f'[{address}]'
            v_line = 'Via: SIP/2.0/UDP ' + \
                     f'{address}:{h_via["address"][1]}'
            if 'branch' in h_via.keys():
                v_line += f';branch={h_via["branch"]}'
            if 'rport' in h_via.keys():
                if h_via["rport"] is not None:
                    v_line += f';rport={h_via["rport"]}'
                else:
                    v_line += ';rport'
            if 'received' in h_via.keys():
                v_line += f';received={h_via["received"]}'
            v_line += "\r\n"
            via += v_line
        return via

    def invite(self, number: str, ms: Dict[int, Dict[str, 'RTP.PayloadType']],
               sendtype: 'RTP.TransmitType') -> Tuple[SIPMessage, str, int]:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        branch = "z9hG4bK" + self.gen_call_id()[0:25]
        call_id = self.gen_call_id()
        sess_id = self.sessID.next()
        invite = self.genInvite(number, str(sess_id), ms, sendtype, branch,
                                call_id)
        self.recvLock.acquire()
        self.send_message(invite)
        debug('Invited')
        response = SIPMessage(self.s.recv(8192))
        debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message invite 1\n----\n{response.raw}\n----\n")

        while ((response.status != SIPStatus(401) and
                response.status != SIPStatus(100) and
                response.status != SIPStatus(180)) or
               response.headers['Call-ID'] != call_id):
            if not self.NSD:
                break
            self.parse_message(response)
            response = SIPMessage(self.s.recv(8192))
            debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message invite 2\n----\n{response.raw}\n----\n")

        if (response.status == SIPStatus(100) or
           response.status == SIPStatus(180)):
            return SIPMessage(invite.encode('utf8')), call_id, sess_id
        debug(f"Received Response: {response.summary()}")
        ack = self.gen_ack(response)
        self.send_message(ack)
        debug("Acknowledged")
        authhash = self.gen_authorization(response)
        nonce = response.authentication['nonce']
        realm = response.authentication['realm']
        auth = f'Authorization: Digest username="{self.username}",realm=' + \
               f'"{realm}",nonce="{nonce}",uri="sip:{self.server};' + \
               f'transport=UDP",response="{str(authhash, "utf8")}",' + \
               'algorithm=MD5\r\n'

        invite = self.genInvite(number, str(sess_id), ms, sendtype, branch,
                                call_id)
        invite = invite.replace('\r\nContent-Length',
                                f'\r\n{auth}Content-Length')

        self.send_message(invite)

        self.recvLock.release()

        return SIPMessage(invite.encode('utf8')), call_id, sess_id

    def bye(self, request: SIPMessage) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        message = self.gen_bye(request)
        # TODO: Handle bye to server vs. bye to connected client
        self.send_message(message)

    def deregister(self) -> bool:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        self.recvLock.acquire()
        firstRequest = self.gen_first_response(deregister=True)
        self.send_message(firstRequest)

        self.out.setblocking(False)

        ready = select.select([self.out], [], [], self.register_timeout)
        if ready[0]:
            resp = self.s.recv(8192)
            debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message deregister 1\n----\n{resp}\n----\n")
        else:
            raise TimeoutError('Deregistering on SIP Server timed out')

        response = SIPMessage(resp)

        if response.status == SIPStatus(401):
            # Unauthorized, likely due to being password protected.
            regRequest = self.gen_register(response, deregister=True)
            self.send_message(regRequest)
            ready = select.select([self.s], [], [], self.register_timeout)
            if ready[0]:
                resp = self.s.recv(8192)
                debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message deregister 2\n----\n{resp}\n----\n")
                response = SIPMessage(resp)
                if response.status == SIPStatus(401):
                    # At this point, it's reasonable to assume that
                    # this is caused by invalid credentials.
                    debug("Unauthorized")
                    raise InvalidAccountInfoError("Invalid Username or " +
                                                  "Password for SIP server " +
                                                  f"{self.server}:" +
                                                  f"{self.myPort}")
                elif response.status == SIPStatus(400):
                    # Bad Request
                    # TODO: implement
                    # TODO: check if broken connection can be brought back
                    # with new urn:uuid or reply with expire 0
                    self._handle_bad_request()
            else:
                raise TimeoutError('Deregistering on SIP Server timed out')

        if response.status == SIPStatus(500):
            self.recvLock.release()
            time.sleep(5)
            return self.deregister()

        if response.status == SIPStatus.OK:
            self.recvLock.release()
            return True
        self.recvLock.release()
        return False

    def register(self) -> bool:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        self.recvLock.acquire()
        firstRequest = self.gen_first_response()
        self.send_message(firstRequest)

        self.out.setblocking(False)

        ready = select.select([self.out], [], [], self.register_timeout)
        if ready[0]:
            resp = self.s.recv(8192)
            debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message register 1\n----\n{resp}\n----\n")
        else:
            raise TimeoutError('Registering on SIP Server timed out')

        response = SIPMessage(resp)
        if len(response.headers['Via']) > 0 and 'received' in response.headers['Via'][0] \
                and 'rport' in response.headers['Via'][0]:
            self.my_public_ip = response.headers['Via'][0]['received']
            self.my_public_port = response.headers['Via'][0]['rport']
            debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} after received Message register 1"
                  f" received {self.my_public_ip} rport {self.my_public_port}")

        if response.status == SIPStatus.TRYING:
            response = SIPMessage(self.s.recv(8192))
            debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message register 2\n----\n{response.raw}\n----\n")
        if response.status == SIPStatus(400):
            # Bad Request
            # TODO: implement
            # TODO: check if broken connection can be brought back
            # with new urn:uuid or reply with expire 0
            self._handle_bad_request()

        if response.status == SIPStatus(401):
            # Unauthorized, likely due to being password protected.
            regRequest = self.gen_register(response)
            self.send_message(regRequest)
            ready = select.select([self.s], [], [], self.register_timeout)
            if ready[0]:
                resp = self.s.recv(8192)
                response = SIPMessage(resp)
                debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message register 3\n----\n{resp}\n----\n")
                if response.status == SIPStatus(401):
                    # At this point, it's reasonable to assume that
                    # this is caused by invalid credentials.
                    debug("Unauthorized")
                    raise InvalidAccountInfoError("Invalid Username or " +
                                                  "Password for SIP server " +
                                                  f"{self.server}:" +
                                                  f"{self.myPort}")
                elif response.status == SIPStatus(400):
                    # Bad Request
                    # TODO: implement
                    # TODO: check if broken connection can be brought back
                    # with new urn:uuid or reply with expire 0
                    self._handle_bad_request()
            else:
                raise TimeoutError('Registering on SIP Server timed out')

        if response.status == SIPStatus(407):
            # Proxy Authentication Required
            # TODO: implement
            debug('Proxy auth required')

        # TODO: This must be done more reliable
        if response.status not in [
                SIPStatus(400),
                SIPStatus(401),
                SIPStatus(407)]:
            # Unauthorized
            if response.status == SIPStatus(500):
                self.recvLock.release()
                time.sleep(5)
                return self.register()
            else:
                # TODO: determine if needed here
                self.parse_message(response)

        self.recvLock.release()
        if response.status == SIPStatus.OK:
            if self.NSD:
                # When working with SIP notify keep alive this is not need and not good
                # When the timer ends a new register is started.
                # self.registerThread = Timer(self.default_expires - 5, self.register)
                self.registerThread = Timer(self.default_expires - 5, self.check_for_new_register)
                self.registerThread.name = "SIP Register CSeq: " + \
                                           f"{self.registerCounter.x}"
                self.registerThread.start()
            return True
        else:
            raise InvalidAccountInfoError("Invalid Username or Password for " +
                                          f"SIP server {self.server}:" +
                                          f"{self.myPort}")

    def check_for_new_register(self):
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} '
              f'start with use keep alive {self.use_keep_alive}')
        if self.use_keep_alive:
            return
        self.register()

    def _handle_bad_request(self) -> None:
        # Bad Request
        # TODO: implement
        # TODO: check if broken connection can be brought back
        # with new urn:uuid or reply with expire 0
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} Bad Request')

    def subscribe(self, lastresponse: SIPMessage) -> None:
        debug(f'{self.__class__.__name__}.{inspect.stack()[0][3]} called from '
              f'{inspect.stack()[1][0].f_locals["self"].__class__.__name__}.{inspect.stack()[1][3]} start')
        # TODO: check if needed and maybe implement fully
        self.recvLock.acquire()
        subRequest = self.gen_subscribe(lastresponse)
        self.send_message(subRequest)
        response = SIPMessage(self.s.recv(8192))
        debug(f"{self.__class__.__name__}.{inspect.stack()[0][3]} <-- received Message subscribe\n----\n {response.raw}\n----\n")
        debug(f'Got response to subscribe: {response.heading}')

        self.recvLock.release()
