#!/usr/bin/env python
# coding=utf-8

import time
import os
import sys
import shutil
import argparse
from stat import S_ISDIR

from machinetalk_lib import service
from machinetalk_core.remotefile.fileservicebase import FileServiceBase

from machinetalk.protobuf.message_pb2 import Container
from machinetalk.protobuf.config_pb2 import CLEARTEXT


class FileService(FileServiceBase):
    def __init__(self, path, debug):
        super(FileService, self).__init__(debuglevel=int(debug))
        self.debug = debug
        self.path = path
        self._check_path()
        self.tx = Container()

    def start_service(self):
        self.start()
        self._create_service_announcement()
        self._announcement.publish()

    def stop_service(self):
        self._announcement.unpublish()
        self.stop()

    def _create_service_announcement(self):
        uuid, remote = service.read_machinetalk_ini()
        hostname = '%(fqdn)s'  # replaced by service announcement
        name = 'File2 on %s' % hostname
        dsn = self.file2_dsn.replace('0.0.0.0', hostname)
        port = self.file2_port
        self._announcement = service.Service(
            type_='file2',
            svc_uuid=uuid,
            dsn=dsn,
            port=port,
            host=hostname,
            name=name,
            loopback=(not remote),
            debug=self.debug)

    def _check_path(self):
        if not os.path.exists(self.path):
            sys.stderr.write('specified path %s does not exist\n' % self.path)
            sys.exit(1)

    def _send_error_message(self, identity, note):
        if self.debug:
            print('error: %s' % note)
        self.tx.note.append(note)
        self.send_error(identity, self.tx)

    # handle received messages
    def file_get_received(self, identity, rx):
        if not rx.HasField('file_service_data') or len(rx.file_service_data.files) < 1:
            self._send_error_message(identity, 'invalid arguments')
            return

        file_item = rx.file_service_data.files[0]
        file_name = file_item.name
        pathname = os.path.join(self.path, file_name)

        if not os.path.exists(pathname) or os.path.isdir(pathname):
            self._send_error_message(identity, 'file not found: %s' % pathname)
            return

        try:
            file_buffer = open(pathname, 'rb').read()
        except OSError:
            self._send_error_message(identity, 'error reading file')
            return
        file_item = self.tx.file_service_data.files.add()
        file_item.blob = file_buffer
        file_item.encoding = CLEARTEXT
        file_item.name = file_name

        self.send_file_data(identity, self.tx)

    def file_put_received(self, identity, rx):
        if not rx.HasField('file_service_data') or len(rx.file_service_data.files) < 1:
            self._send_error_message(identity, 'invalid arguments')
            return

        file_item = rx.file_service_data.files[0]
        pathname = os.path.join(self.path, file_item.name)

        if file_item.encoding is not CLEARTEXT:
            self._send_error_message(identity, 'only supports cleartext encoding')
            return

        f = None
        try:
            f = open(pathname, 'wb')
            f.write(file_item.blob)
        except OSError or IOError:
            if f:
                f.close()
            self._send_error_message(identity, 'cannot write file %s' % pathname)
            return

        self.send_cmd_complete(identity, self.tx)

    def file_ls_received(self, identity, rx):
        if not rx.HasField('file_service_data') or len(rx.file_service_data.files) < 1:
            self._send_error_message(identity, 'invalid arguments')
            return

        file_item = rx.file_service_data.files[0]
        file_path = file_item.name
        pathname = os.path.join(self.path, file_path)

        try:
            files = os.listdir(pathname)
        except OSError:
            self._send_error_message(identity, 'error listing directory %s' % pathname)
            return

        for entry in sorted(files):
            file_item = self.tx.file_service_data.files.add()
            filepath = os.path.join(pathname, entry)
            file_item.name = os.path.join(file_path, entry)
            statinfo = os.stat(filepath)
            mode = statinfo.st_mode
            file_item.is_dir = S_ISDIR(mode)
            file_item.last_modified = int(statinfo.st_mtime)
            file_item.size = statinfo.st_size

        self.send_file_listing(identity, self.tx)

    def file_mkdir_received(self, identity, rx):
        if not rx.HasField('file_service_data') or len(rx.file_service_data.files) < 1:
            self._send_error_message(identity, 'invalid arguments')
            return

        file_item = rx.file_service_data.files[0]
        pathname = os.path.join(self.path, file_item.name)

        try:
            os.mkdir(pathname)
        except OSError or os.FileExistsError:
            self._send_error_message(identity, 'error creating directory')
            return

        self.send_cmd_complete(self.tx)

    def file_delete_received(self, identity, rx):
        if not rx.HasField('file_service_data') or len(rx.file_service_data.files) < 1:
            self._send_error_message(identity, 'invalid arguments')
            return

        file_item = rx.file_service_data.files[0]
        pathname = os.path.join(self.path, file_item.name)

        if pathname is self.path:
            self._send_error_message(identity, 'cannot delete root directory')
            return

        if not os.path.exists(pathname) or os.path.isdir(pathname):
            self._send_error_message(identity, 'file or directory not found')
            return

        try:
            if os.path.isdir(pathname):
                shutil.rmtree(pathname)
            else:
                os.remove(pathname)
        except OSError:
            self._send_error_message(identity, 'error removing file or directory')
            return

        self.send_cmd_complete(identity, self.tx)

    def ping_received(self, identity, _):
        self.send_ping_acknowledge(identity, self.tx)


def main():
    parser = argparse.ArgumentParser(description='Implementation of the file service')
    parser.add_argument('-p', '--path', help='Path to the directory to serve', default=".")
    parser.add_argument('-d', '--debug', help='Enable debug mode', action='store_true')

    args = parser.parse_args()
    debug = args.debug
    path = args.path

    file_service = FileService(path=path, debug=debug)
    file_service.file2_uri = 'tcp://*'
    file_service.start_service()

    try:
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print('exiting file server')
        file_service.stop_service()


if __name__ == '__main__':
    main()
