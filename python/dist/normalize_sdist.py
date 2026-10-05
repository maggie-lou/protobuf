# Protocol Buffers - Google's data interchange format
# Copyright 2026 Google Inc. All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Remove build-specific metadata from a setuptools source distribution.

setuptools stamps the current time into the gzip header and tar entries, so
building the same sources twice produces different archives. This rewrites the
archive with the same files but fixed metadata.

Usage: normalize_sdist.py <input.tar.gz> <output.tar.gz>
"""

import gzip
import sys
import tarfile


def normalize_sdist(source, destination):
  """Preserve archive contents while making ordering and metadata reproducible."""
  with tarfile.open(source, 'r:gz') as original:
    with open(destination, 'wb') as output:
      # Fix the gzip header timestamp. An empty filename also prevents the
      # output path entering the gzip header.
      with gzip.GzipFile(
          filename='', mode='wb', fileobj=output, mtime=0
      ) as compressed:
        with tarfile.open(
            fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT
        ) as archive:
          # Write entries in a fixed order, independent of how setuptools
          # walked the file system.
          for member in sorted(
              original.getmembers(), key=lambda member: member.name
          ):
            # Clear per-entry timestamps and the building user's identity.
            member.mtime = 0
            member.uid = member.gid = 0
            member.uname = member.gname = ''
            # PAX values override the corresponding TarInfo fields when read,
            # so drop them too. setuptools writes fractional PAX timestamps
            # for files it generates, such as PKG-INFO.
            member.pax_headers = {
                key: value for key, value in member.pax_headers.items()
                if key not in (
                    'mtime', 'atime', 'ctime', 'uid', 'gid', 'uname', 'gname'
                )
            }
            # Copy file contents unchanged. Directories and links have no
            # contents, only the entry itself.
            if member.isfile():
              with original.extractfile(member) as contents:
                archive.addfile(member, contents)
            else:
              archive.addfile(member)


if __name__ == '__main__':
  normalize_sdist(sys.argv[1], sys.argv[2])
