#!/usr/bin/env python
#
# Copyright (c) 2010, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""
This file contains the copy database operation which ensures a database
is exactly the same among two servers.
"""

import sys
from mysql.utilities.exception import UtilError

def copy_db(src_val, dest_val, db_list, options):
    """Copy a database

    This method will copy a database and all of its objects and data from
    one server (source) to another (destination). Options are available to
    selectively ignore each type of object. The force parameter is
    used to permit the copy to overwrite an existing destination database
    (default is to not overwrite).

    src_val[in]        a dictionary containing connection information for the
                       source including:
                       (user, password, host, port, socket)
    dest_val[in]       a dictionary containing connection information for the
                       destination including:
                       (user, password, host, port, socket)
    options[in]        a dictionary containing the options for the copy:
                       (skip_tables, skip_views, skip_triggers, skip_procs,
                       skip_funcs, skip_events, skip_grants, skip_create,
                       skip_data, copy_dir, verbose, force, quiet,
                       connections, debug, exclude_names, exclude_patterns)

    Notes:
        copy_dir - a directory to use for temporary files (default is None)
        force    - if True, the database on the destination will be dropped
                   if it exists (default is False)
        quiet    - do not print any information during operation
                   (default is False)

    Returns bool True = success, False = error
    """

    from mysql.utilities.common.database import Database
    from mysql.utilities.common.server import connect_servers

    quiet = options.get("quiet", False)
    skip_views = options.get("skip_views", False)
    skip_procs = options.get("skip_procs", False)
    skip_funcs = options.get("skip_funcs", False)
    skip_events = options.get("skip_events", False)
    skip_grants = options.get("skip_grants", False)

    conn_options = {
        'quiet'     : quiet,
        'version'   : "5.1.30",
    }
    servers = connect_servers(src_val, dest_val, conn_options)

    source = servers[0]
    destination = servers[1]

    cloning = (src_val == dest_val) or dest_val is None
    
    # Get list of all databases from source if --all is specified.
    # Ignore system databases.
    if options.get("all", False):
        # The --all option is valid only if not cloning.
        if not cloning:
            if not quiet:
                print "# Including all databases."
            rows = source.get_all_databases()
            for row in rows:
                db_list.append((row[0], None)) # Keep same name
        else:
            raise UtilError("Cannot copy all databases on the same server.")

    # Check user permissions on source and destination for all databases
    for db_name in db_list:
        source_db = Database(source, db_name[0])
        if destination is None:
            destination = source
        if db_name[1] is None:
            db = db_name[0]
        else:
            db = db_name[1]
        dest_db = Database(destination, db)
        
        # Make a dictionary of the options
        access_options = {
            'skip_views'  : skip_views,
            'skip_procs'  : skip_procs,
            'skip_funcs'  : skip_funcs,
            'skip_grants' : skip_grants,
            'skip_events' : skip_events,
        }

        source_db.check_read_access(src_val["user"], src_val["host"],
                                    access_options)
        
        dest_db.check_write_access(dest_val['user'], dest_val['host'],
                                   access_options)

    for db_name in db_list:

        # Error is source db and destination db are the same and we're cloning
        if destination == source and db_name[0] == db_name[1]:
            raise UtilError("Destination database name is same as "
                                 "source - source = %s, destination = %s" %
                                 (db_name[0], db_name[1]))

        # Display copy message
        if not quiet:
            msg = "# Copying database %s " % db_name[0]
            if db_name[1]:
                msg += "renamed as %s" % (db_name[1])
            print msg

        # Get a Database class instance
        db = Database(source, db_name[0], options)

        # Error is source database does not exist
        if not db.exists():
            raise UtilError("Source database does not exist - %s" %
                                 db_name[0])

        # Perform the copy
        db.init()
        db.copy(db_name[1], None, options, destination,
                options.get("threads", False))

    if not quiet:
        print "#...done."
    return True
