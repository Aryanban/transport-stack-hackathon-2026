# PROBLEM 1 BUS TRAVEL TIME

﻿Problem 1 / Phase 1
Real-time bus traffic model and journey planner
Phase
	Phase 1, open to all registered teams
	Core data
	Real-time and historical bus GPS, static GTFS (routes, stops, schedules)
	You build
	A travel-time model and an API that returns bus journey options between two points
	Judged on
	Accuracy of travel-time estimates against observed trips and Google Maps
	1        Background
Delhi has several thousand buses on the road. Each bus sends its location every few seconds. If you know where a bus was and when, you know how fast it moved. Put thousands of buses together and you get a picture of traffic on most major roads, at every hour of the day.
Today, bus journey times in Delhi are hard to predict. The published timetable assumes fixed travel times. Real travel times change with the hour, the day and the road. A commuter cannot tell whether a trip will take 30 minutes or 60. This problem asks you to use the bus fleet as a set of moving sensors, and turn its signal into travel times a commuter can rely on.
2        The challenge
Build a model of bus travel times from real-time and historical bus locations. Then build a journey planner on top of it. A user gives an origin, a destination and a departure time. Your system returns sensible bus journeys and how long each will take.
2.1        What the system should do
* Accept an origin and a destination, as coordinates or stop names, and a departure time.
* Return one or more journey options. Each option lists the walk to the first stop, the boarding stop, the route, the stop to get off at, any transfers, the walk to the destination, and the total time.
* Estimate time on the bus from your model of how fast buses actually move, not only from the timetable.
* Give different answers at different times. A trip at 9 am on a weekday should not get the same estimate as the same trip at 11 pm.
* Expose all of this as an API, with a simple screen or client that shows the results.
2.2        An example
A user asks: from Kashmere Gate ISBT to Nehru Place, leaving at 8:30 am on a Tuesday. A good answer shows two or three options. For each, it gives the routes to take, where to change, how long to walk, and an estimated arrival time. It also says how long the same trip would usually take at a quieter hour, so the user can see the effect of traffic.
2.3        Scope
The focus is bus journeys. Include walking to and from stops in the total journey time. Multimodal journeys are a welcome extension but not required.
3        Data provided
3.1        Real-time vehicle positions (GTFS-RT)
GTFS-RT is a standard format for live transit data. The feed gives the current position of each DTC and cluster bus, updated every few seconds.
Field
	Description
	vehicle_id
	Unique identifier of the bus
	route_id
	Route the bus is running on; joins to static GTFS routes.txt
	latitude, longitude
	Position of the bus
	timestamp
	Time of the position update
	3.2        Historical GPS traces
Past vehicle positions with the same fields, covering several weeks. Use these to learn how speeds change by hour of day and day of week. Exact period and format (to be confirmed).
3.3        Static GTFS
GTFS is the standard format for transit schedules. The Delhi bus feed has about 10,500 stops, 2,400 routes and 89,000 scheduled trips. The main files are stops.txt (stop locations), routes.txt (route names), trips.txt (each scheduled run), stop_times.txt (the timetable) and shapes.txt (the path each route follows on the road).
4        Expected deliverables
* A documented API, for example GET /journeys?from=…&to=…&depart=…, that returns journey options as JSON.
* A simple map-based or web screen, or an API client, to inspect the results.
* A short technical note. Explain how you link GPS points to roads or routes, how you estimate travel time on each stretch of road, and how you combine live and historical data.
* A validation report. Pick a set of origin–destination pairs. Compare your estimates with actual bus trip times and with Google Maps for the same pairs and times.
* Code and instructions that let someone else run your system.
5        Things to think about
* GPS points are noisy and irregular. Some jump off the road. Some arrive late or not at all.
* A bus waits at stops and at traffic signals. That waiting is part of travel time. Decide whether to treat it separately.
* Some roads have few buses at some hours. Explain what your model does when there is little or no live data.
6        Data access
All datasets for this problem are shared through the Delhi Transport Stack platform. Register at delhi.transportstack.in and request access to the datasets you need. Bus schedules follow the GTFS Schedule standard and live positions follow GTFS Realtime.
Questions about the problems or data: csm@iiitd.ac.in.
Transport Stack Hackathon 2026  /  delhi.transportstack.in/hackathon
