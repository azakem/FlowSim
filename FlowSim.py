import os
import sys
import traceback
import time
import threading
from threading import Timer
import subprocess
import re
import csv
import math

""" Simulate flows given in input file using iperf, and write results to output file
	
	E.g.:

	python FlowSim.py flows.txt sim_stats.csv

	Will read flow information from flows.txt and write results to sim_stats.csv 

	This script expects that the format of the input flows file is:

	time,src_ip,src_port,dst_ip,dst_port,size
	t1,sip1,sp1,dip1,dp2,s1
	t2,sip2,sp2,dip2,dp2,s2
	...
	tn,sipn,spn,dipn,dpn,sn

	Where time is given in seconds, and size is give in bytes.

	Note: to support large number of concurrent flows, the maximum number of open files descriptors
	will likely need to be increased. 

	To see the maximum number of open file descriptors on a linux machine, try:

	cat /proc/sys/fs/file-max

	To increase maximum number of file descriptors to 10000, try:

	su -
	sysctl -w fs.file-max=100000

	To have limit remain at 10000 after reboot, edit /etc/sysctl.conf and append the line:
	fs.file-max = 100000
"""

	##TODO 
	##Mark time when script first started; after flow file is read and servers are started, 
	##Check delta between time started and current time, sleep for 60 seconds - delta
	##Append start date/hour/minute to output file name


write_lock = threading.Lock() # lock for writing to output file
all_finished = threading.Event() # event for signalling when all flows have completed

class flow:
	"""Object for storing flow information"""

	def __init__(self):
		start_time = 0
		src_ip = ""
		src_port = 0
		dst_ip = ""
		dst_port = 0 
		flow_size = 0 

def parseFlow(row): 
	"""Parse flow information from a row of the input file, return flow object"""
	new_flow = flow()
	try: 
		new_flow.start_time = float(row[0])
		new_flow.src_ip = row[1]
		new_flow.src_port = int(row[2])
		new_flow.dst_ip = row[3]
		new_flow.dst_port = int(row[4])
		new_flow.flow_size = int(math.ceil(float(row[5])))
		return new_flow
	except:
		traceback.print_exc()

def scheduleFlows(flows, output_filepath):
	""" schedule execution of iperf tasks to simulate flows, set all_finished event when all iperf clients have finished"""
	flow_id = 0
	iperf_client_threads = list()
	for flow in flows:
		p = Timer(float(flow.start_time)/1000, simulateFlow, (flow_id, flow, output_filepath))
		p.start()
		flow_id += 1
		iperf_client_threads.append(p)
	for p in iperf_client_threads:
		p.join()
	all_finished.set()

def simulateFlow(flow_id, flow, output_filepath):
	""" execute an iperf client for a given flow, and write flow id, duration, and bandwidth to output file"""
	try:
		print "flow {} starting".format(flow_id)
		cmd_line = ["/usr/bin/iperf", "-c", str(flow.dst_ip), "-p", str(flow.dst_port), "-n", str(flow.flow_size)]
		p = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = p.communicate()
		p.wait()
	except:
		traceback.print_exc()

	print "flow {} finished".format(flow_id)

	""" Lines below parse output from iperf; example output is shown below:

	------------------------------------------------------------
	Client connecting to 127.0.0.1, TCP port 10000
	TCP window size: 2.50 MByte (default)
	------------------------------------------------------------
	[  3] local 127.0.0.1 port 49322 connected with 127.0.0.1 port 10000
	[ ID] Interval       Transfer     Bandwidth
	[  3]  0.0- 0.0 sec   128 KBytes  27.6 Gbits/sec
	"""

	print out
	interval_string = re.findall("[0-9]+\.?[0-9]+- [0-9]+\.?[0-9]+ sec", out)[0]
	bandwidth_string = re.findall("[0-9]+\.?[0-9]+ [a-zA-Z]+/sec", out)[0]

	interval = re.findall("[0-9]+\.?[0-9]+", interval_string)
	duration = float(interval[1]) - float(interval[0])

	bandwidth_val = float(re.findall("[0-9]+\.?[0-9]+", bandwidth_string)[0])
	bandwidth_unit = re.findall("[a-zA-Z]+", bandwidth_string)[0]

	if bandwidth_unit == 'G':
		bandwidth = bandwidth_val * 1000000
	elif bandwidth_unit == 'M':
		bandwidth = bandwidth_val * 1000
	else:
		bandwidth = bandwidth_val

	with(write_lock):
		try: 
			with open(output_filepath, 'ab') as output:
				writer = csv.writer(output)
				output_row = [flow_id, duration, bandwidth]
				writer.writerow(output_row)
		except:
			print("Error writing output")
			traceback.print_exc()


def startServers():
	""" Start an iperf server listening to each of ports 11000-11199"""
	server_processes = list()
	FNULL = open(os.devnull, 'w')
	for i in range(11000, 11200):
		cmd_line = ["/usr/bin/iperf", "-s", "-p", str(i)]
		p = subprocess.Popen(cmd_line, stdout=FNULL, close_fds=True)
		server_processes.append(p)
	return server_processes

def killServers(server_processes):
	""" Terminate the iperf servers""" 
	for p in server_processes:
		p.terminate()

def main(argv): 

	validate_args(argv)

	flow_filepath = argv[0]
	output_filepath = argv[1]
	flows = list()

	# write header line to output file
	try: 
		with open(output_filepath, 'wb') as output:
			writer = csv.writer(output)
			header_row = ["flow_id","duration(s)","bandwidth(Kbps)"]
			writer.writerow(header_row)
	except:
		print("Error writing to output file")
		traceback.print_exc()
		sys.exit(-1)

	# read input file and parse flow information
	try:
		with open(flow_filepath, 'r') as input:
			input.readline() # discard header row
			reader = csv.reader(input)

			for row in reader:
				flow = parseFlow(row)
				flows.append(flow)
	except:
		print("Error reading input file")
		traceback.print_exc()
		sys.exit(-1)

	all_finished.clear()
	# start iperf servers
	server_processes = startServers()
	# schedule and execute outgoing flows
	scheduleFlows(flows, output_filepath)

	# after all outgoing flows have completed, wait ten minutes, then terminate servers
	# this is pretty arbitrary; preferable to manually terminate after simulation is finished?
	# or specify time to wait before terminating servers as a command line argument?
	# otherwise, need machines to somehow signal each other when they have completed outgoing flows
	all_finished.wait()
	print ("All outgoing flows completed, servers terminating in ten minutes...")
	time.sleep(600)
	killServers(server_processes)
	print "Output written to {}".format(output_filepath)

def validate_args(argv):
	"""Basic validation of command line arguments"""
	if len(argv) < 2:
		print "Insufficient command line arguments"
		usage()
		sys.exit(-1)
	if len(argv) > 2:
		print "Too many command line arguments, extra arguments ignored"

def usage():
	"""Print usage message"""
	print "Usage: python FlowSim.py <input_file> <output_file>"

if __name__ == '__main__':
	main(sys.argv[1:])