# Protocol Buffers - Google's data interchange format
# Copyright 2026 Google Inc. All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Tests for reproducible source distributions."""

import gzip
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

import normalize_sdist


class NormalizeSdistTest(unittest.TestCase):

  def make_archive(self, path, timestamp, reverse):
    with open(path, 'wb') as output:
      with gzip.GzipFile(
          filename=path.name, mode='wb', fileobj=output, mtime=timestamp
      ) as compressed:
        with tarfile.open(
            fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT
        ) as archive:
          directory = tarfile.TarInfo('protobuf-1.0')
          directory.type = tarfile.DIRTYPE
          directory.mode = 0o755
          file = tarfile.TarInfo('protobuf-1.0/' + 'long_name_' * 15 + '.py')
          contents = b'print("protobuf")\n'
          file.size = len(contents)
          file.mode = 0o755
          link = tarfile.TarInfo('protobuf-1.0/link')
          link.type = tarfile.SYMTYPE
          link.linkname = file.name.removeprefix('protobuf-1.0/')
          members = [(directory, None), (file, contents), (link, None)]
          if reverse:
            members.reverse()
          for member, data in members:
            member.uid = member.gid = timestamp
            member.uname = member.gname = str(timestamp)
            member.mtime = timestamp
            member.pax_headers = {
                'mtime': str(timestamp + 0.5),
                'atime': str(timestamp),
                'ctime': str(timestamp),
            }
            archive.addfile(member, io.BytesIO(data) if data is not None else None)

  def test_metadata_and_order_do_not_change_archive_bytes(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      first, second = root / 'first.tar.gz', root / 'second.tar.gz'
      self.make_archive(first, 1000, False)
      self.make_archive(second, 2000, True)
      outputs = [root / 'output-a.tar.gz', root / 'output-b.tar.gz']
      for source, output in zip((first, second), outputs):
        normalize_sdist.normalize_sdist(source, output)
      self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
      self.assertEqual(outputs[0].read_bytes()[4:8], b'\0\0\0\0')
      with tarfile.open(outputs[0]) as archive:
        members = archive.getmembers()
        self.assertEqual(
            [member.name for member in members],
            sorted(member.name for member in members),
        )
        file = next(member for member in members if member.isfile())
        self.assertEqual(archive.extractfile(file).read(), b'print("protobuf")\n')
        self.assertEqual(file.mode, 0o755)
        link = next(member for member in members if member.issym())
        self.assertEqual(
            link.linkname, file.name.removeprefix('protobuf-1.0/')
        )
        self.assertTrue(any(member.isdir() for member in members))
        for member in members:
          self.assertEqual((member.mtime, member.uid, member.gid), (0, 0, 0))
          self.assertEqual((member.uname, member.gname), ('', ''))
          self.assertNotIn('atime', member.pax_headers)
          self.assertNotIn('ctime', member.pax_headers)


if __name__ == '__main__':
  unittest.main()
