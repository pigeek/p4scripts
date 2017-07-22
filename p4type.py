#
# This script is public domain, with not warranty or guarantee of functionality
# This script was written to minimize server-side load for highly scaled servers
#
# https://github.com/gorlak/p4scripts
#

# core python
import locale
import optparse
import os
import re

# p4api
import P4

#
# setup argument parsing
#

parser = optparse.OptionParser()
parser.add_option( "-e", "--exact", dest="select_exact", action="store", default=None, help="list the depot path of the files that match the specified fully-qualified type (including attributes and storage)" )
parser.add_option( "-b", "--base", dest="select_base", action="store", default=None, help="list the depot path of the files whose base type match the specified base type (not including attributes and storage)" )
parser.add_option( "-E", "--set-exact", dest="set_exact", action="store", default=None, help="set the new file type" )
parser.add_option( "-B", "--set-base", dest="set_base", action="store", default=None, help="change the base file type, but preserve attributes and storage" )
( options, args ) = parser.parse_args()

import pprint
pp = pprint.PrettyPrinter( indent=4 )

if os.name != "nt":
	print( "Not tested outside of windows\n" )
	exit( 1 )

#
# main
#

try:

	#
	# connect and setup p4
	#

	p4 = P4.P4()
	p4.connect()

	# handle non-unicode servers by marshalling raw bytes to local encoding
	if not p4.server_unicode:
		p4.encoding = 'raw'

	def p4MarshalString( data ):
		if isinstance( data, str ):
			return data
		else:
			return data.decode( locale.getpreferredencoding() )

	#
	# query lots of info
	#

	p4Types = dict ()
	print( "Fetching file information..." )
	results = p4.run_fstat('-Os', '-F', '^headAction=delete & ^headAction=move/delete', '...')
	for result in results:
		f = result[ 'depotFile' ]
		f = p4MarshalString( f )
		t = result[ 'headType' ]
		t = p4MarshalString( t )
		if not t in p4Types:
			p4Types[ t ] = list ()
		p4Types[ t ].append( f )

	#
	# select the list of files we care about
	#

	files = list ()

	if options.select_exact:
		if options.select_exact in p4Types:
			for f in sorted( p4Types[ options.select_exact ] ):
				files.append( ( f, options.select_exact ) )

	if options.select_base:
		for k, v in p4Types.items():
			if k.startswith( options.select_base ):
				for f in v:
					files.append( ( f, k ) )

	#
	# make changes, if desired. list selection otherwise
	#

	# symlink omitted because it's different
	validBaseTypes = [ 'text', 'binary', 'apple', 'resource', 'unicode', 'utf8', 'utf16' ]

	if options.set_exact:

		print( "Setting type to " + options.set_exact + "...")

		for f in sorted( files ):
			p4.run_edit('-t', options.set_exact, f[0])

	elif options.set_base:
		
		if options.set_base not in validBaseTypes:
			print( "Desired base type " + options.set_base + " is not a recognized base type")
			os.exit( 1 )
		
		print( "Changing base type to " + options.set_base + "...")

		for f in sorted( files ):

			# determine the current base filetype
			base = None
			for b in validBaseTypes:
				if f[1].startswith( b ):
					base = b
					break

			if not base:
				print( "Existing type " + f[1] + " has unrecognized base type" )
				os.exit( 1 )

			# transplant flags onto the new base filetype
			newBase = f[1].replace( base, options.set_base )

			p4.run_edit( '-t', newBase, f[0] )

	else:
		print( "Total Type breakdown:" )
		for k, v in sorted( p4Types.items() ):
			print( " got " + str( len( v ) ) + " files of type " + k )

		if len( files ):
			print( "Files:" )
			for f in sorted( files ):
				print( f[0] )

	#
	# disconnect
	#

	p4.disconnect()

except P4.P4Exception:
	for e in p4.errors:
		print( e )

except KeyboardInterrupt:
	exit( 1 )