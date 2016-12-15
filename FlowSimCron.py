import os
import sys
import time
import subprocess

""" Create a job in cron to execute FlowSim.py at the specified hour and minute of the current day
	The time, path to FlowSim.py, input filepath, and output filepath must be provided as arguments
	In addition, a cron file must exist for the current user

	E.g.:

	python FlowSimCron.py 14:00 /home/FlowSim.py /home/input_flows /home/output.csv

	Will schedule execution of FlowSim.py at 2:00pm, with FlowSim.py located at /home/FlowSim.py, 
	the flows input file located at /home/input_flows, and the output file written to /home/output.csv
	"""

	##TODO 
	##Change so that you can specify a number of times to run the experiment, and interval between the experiments
	##Modify cron job creation so that experiment is repeated x times, at interval y

def main(argv):
	hour, minute, simfile, infile, outfile = parseArgs(argv)

	daymonth = time.strftime("%d,%m")
	daymonth_tokens = daymonth.split(",")
	day = daymonth_tokens[0]
	month = daymonth_tokens[1]

	cmd_line = ["crontab", "-l"]
	try:
		with open("mycron", "w") as mycron:
			subprocess.call(cmd_line, stdout=mycron)
	except:
		traceback.print_exc()
		sys.exit(-1)

	flow_sim_cmd = "{} {} {} {} 0-7 python {} {} {}".format(minute, hour, day, month, simfile, infile, outfile)
	cmd_line = ["echo", flow_sim_cmd]
	try:
		with open("mycron", "a") as mycron:
			subprocess.call(cmd_line, stdout=mycron)
	except:
		tracveback.print_exc()
		sys.exit(-1)

	cmd_line = ["crontab", "mycron"]
	try:
		subprocess.call(cmd_line)
	except:
		traceback.print_exc()

	cmd_line = ["rm", "mycron"]
	try:
		subprocess.call(cmd_line)
	except:
		traceback.print_exc()

def parseArgs(argv):
	if (len(argv) < 4):
		print "Error: Insufficient command line arguments"
		usage()
		sys.exit(-1)
	elif (len(argv) > 4):
		print "Error: Too many arguments, extra arguments ignored"

	tokens = argv[0].split(':')
	if (len(tokens) != 2):
		print "Error: time formatted incorrectly, enter as HH:MM (e.g. 14:10)"
		usage()
		sys.exit(-1)
	try: 
		hour = int(tokens[0])
		minute = int(tokens[1])
		if hour < 0 or hour > 23:
			print "Error: hour in time must be between 0 and 23 (e.g., 14:10)"
			usage()
			sys.exit(-1)
		if minute < 0 or minute > 59:
			print "Error: minute in time must be between 0 and 59 (e.g., 14:10)"
			usage()
			sys.exit(-1)
	except:
		print "Error: must provide time as HH:MM (e.g., 14:10)"
		usage()
		sys.exit(-1)
	return hour, minute, argv[1], argv[2], argv[3]

def usage():
	print "Usage: python FlowSimCron <time> <path_to_FlowSim.py> <input_file> <output_File>"

if __name__ == '__main__':
	main(sys.argv[1:])