# coding=utf-8
from fysom import Fysom
from ..common.rpcservice import RpcService

import machinetalk.protobuf.types_pb2 as pb
from machinetalk.protobuf.message_pb2 import Container


class FileServiceBase(object):
    def __init__(self, debuglevel=0, debugname='File Service Base'):
        self.debuglevel = debuglevel
        self.debugname = debugname
        self._error_string = ''
        self.on_error_string_changed = []

        # File2
        self._file2_channel = RpcService(debuglevel=debuglevel)
        self._file2_channel.debugname = '%s - %s' % (self.debugname, 'file2')
        self._file2_channel.on_state_changed.append(self._file2_channel_state_changed)
        self._file2_channel.on_socket_message_received.append(self._file2_channel_message_received)
        # more efficient to reuse protobuf messages
        self._file2_rx = Container()
        self._file2_tx = Container()

        # callbacks
        self.on_file2_message_received = []
        self.on_state_changed = []

        # fsm
        self._fsm = Fysom(
            {'initial': 'down',
             'events': [
                 {'name': 'start', 'src': 'down', 'dst': 'trying'},
                 {'name': 'file2_up', 'src': 'trying', 'dst': 'up'},
                 {'name': 'stop', 'src': 'up', 'dst': 'down'},
             ]}
        )

        self._fsm.ondown = self._on_fsm_down
        self._fsm.onafterstart = self._on_fsm_start
        self._fsm.ontrying = self._on_fsm_trying
        self._fsm.onafterfile2_up = self._on_fsm_file2_up
        self._fsm.onup = self._on_fsm_up
        self._fsm.onafterstop = self._on_fsm_stop

    def _on_fsm_down(self, _):
        if self.debuglevel > 0:
            print('[%s]: state DOWN' % self.debugname)
        for cb in self.on_state_changed:
            cb('down')
        return True

    def _on_fsm_start(self, _):
        if self.debuglevel > 0:
            print('[%s]: event START' % self.debugname)
        self.start_file2_channel()
        return True

    def _on_fsm_trying(self, _):
        if self.debuglevel > 0:
            print('[%s]: state TRYING' % self.debugname)
        for cb in self.on_state_changed:
            cb('trying')
        return True

    def _on_fsm_file2_up(self, _):
        if self.debuglevel > 0:
            print('[%s]: event FILE2 UP' % self.debugname)
        return True

    def _on_fsm_up(self, _):
        if self.debuglevel > 0:
            print('[%s]: state UP' % self.debugname)
        for cb in self.on_state_changed:
            cb('up')
        return True

    def _on_fsm_stop(self, _):
        if self.debuglevel > 0:
            print('[%s]: event STOP' % self.debugname)
        self.stop_file2_channel()
        return True

    @property
    def error_string(self):
        return self._error_string

    @error_string.setter
    def error_string(self, string):
        if self._error_string is string:
            return
        self._error_string = string
        for cb in self.on_error_string_changed:
            cb(string)

    @property
    def file2_uri(self):
        return self._file2_channel.socket_uri

    @file2_uri.setter
    def file2_uri(self, value):
        self._file2_channel.socket_uri = value

    @property
    def file2_port(self):
        return self._file2_channel.socket_port

    @property
    def file2_dsn(self):
        return self._file2_channel.socket_dsn

    def start(self):
        if self._fsm.isstate('down'):
            self._fsm.start()

    def stop(self):
        if self._fsm.isstate('up'):
            self._fsm.stop()

    def start_file2_channel(self):
        self._file2_channel.start()

    def stop_file2_channel(self):
        self._file2_channel.stop()

    # process all messages received on file2
    def _file2_channel_message_received(self, identity, rx):

        # react to file get message
        if rx.type == pb.MT_FILE_GET:
            self.file_get_received(identity, rx)

        # react to file put message
        elif rx.type == pb.MT_FILE_PUT:
            self.file_put_received(identity, rx)

        # react to file ls message
        elif rx.type == pb.MT_FILE_LS:
            self.file_ls_received(identity, rx)

        # react to file mkdir message
        elif rx.type == pb.MT_FILE_MKDIR:
            self.file_mkdir_received(identity, rx)

        # react to file delete message
        elif rx.type == pb.MT_FILE_DELETE:
            self.file_delete_received(identity, rx)

        for cb in self.on_file2_message_received:
            cb(identity, rx)

    def file_get_received(self, identity, rx):
        print('SLOT file get unimplemented')

    def file_put_received(self, identity, rx):
        print('SLOT file put unimplemented')

    def file_ls_received(self, identity, rx):
        print('SLOT file ls unimplemented')

    def file_mkdir_received(self, identity, rx):
        print('SLOT file mkdir unimplemented')

    def file_delete_received(self, identity, rx):
        print('SLOT file delete unimplemented')

    def send_file2_message(self, identity, msg_type, tx):
        self._file2_channel.send_socket_message(identity, msg_type, tx)

    def send_file_data(self, identity, tx):
        ids = [identity]
        for receiver in ids:
            self.send_file2_message(receiver, pb.MT_FILE_DATA, tx)

    def send_file_listing(self, identity, tx):
        ids = [identity]
        for receiver in ids:
            self.send_file2_message(receiver, pb.MT_FILE_LISTING, tx)

    def send_cmd_complete(self, identity, tx):
        ids = [identity]
        for receiver in ids:
            self.send_file2_message(receiver, pb.MT_CMD_COMPLETE, tx)

    def send_error(self, identity, tx):
        ids = [identity]
        for receiver in ids:
            self.send_file2_message(receiver, pb.MT_ERROR, tx)

    def _file2_channel_state_changed(self, state):

        if state == 'up':
            if self._fsm.isstate('trying'):
                self._fsm.file2_up()
