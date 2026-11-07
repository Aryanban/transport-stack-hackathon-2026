# PROBLEM 4 METRO FEEDER

﻿Problem 4 / Phase 2
Feeder bus routes for metro stations
Phase
	Phase 2, for shortlisted teams
	Core data
	List of target metro stations, metro entry and exit data, road network, bus GPS and stops
	You build
	A feeder route network and fleet plan for about 500 electric buses
	Judged on
	Coverage achieved while meeting every operating constraint
	1        Background
The metro is fast, but only once you are on it. Many people live or work too far from a station to walk. This gap between the station and a person’s home or office is called the first and last mile. When it is hard to cross, people skip the metro and drive or take an auto instead.
Feeder buses are short bus routes that connect neighbourhoods to a metro station. A good feeder network extends the reach of every station. But it only works if the routes fit Delhi’s real roads, real traffic, and the limits of electric buses, which need to be charged during the day.
2        The challenge
Design feeder routes for a given list of metro stations, using a fleet of about 500 electric buses. Aim to serve as many people as possible. Use metro entry and exit data to find where demand is. Plan around EV bus charging.
2.1        Constraints
Every route must meet all of the following:
* Maximum route length of 7 km. These are short local services.
* Account for traffic when you estimate how long a trip takes and how often buses can run.
* Use only roads wider than 6 metres on each side. Narrower roads cannot take a bus safely.
* Electric bus operation. Each bus has a limited range on one charge. Schedules must leave time to charge. Bus specifications, depot and charger locations (make appropriate assumptions).
2.2        What the system should do
* Propose routes for each target station. Give the stops, the path on the road, and the length.
* Share the fleet across routes. Set how often buses run at different times of day.
* Make a charging plan. Every bus must stay within its range for its whole day.
* Report how many people each route, and the whole network, can reach.
2.3        An example
Take one station. Your plan might give it three routes: a 6 km loop through a dense residential area, a 4 km route to a nearby market, and a 7 km route to an area with no current bus service. For each route it lists the stops, the number of buses, a bus every 10 minutes at peak hours and every 20 minutes otherwise, and when and where each bus charges.
3        Data provided
3.1        Target metro stations
The list of metro stations to be served (to be confirmed), with locations.
3.2        Metro entry and exit data
Passenger counts at each station by time of day. Use these to judge how much demand each station has.
3.3        Road network
You may use OpenStreetMap or other sources for road width data.
3.4        Traffic and existing bus service
Historical bus GPS, to estimate road speeds by time of day. Static GTFS, to see existing stops and routes, so that new feeders do not duplicate them.
4        Expected deliverables
* Route paths as GeoJSON, with a list of stops for each route.
* A fleet plan and timetable: buses per route, how often they run by time of day, and trip times.
* A charging schedule, with a check that every bus stays within its range.
* Coverage numbers, such as the share of station demand or population within walking distance of a feeder stop.
* A check that every route meets every constraint above.
* Your code and a short technical note on the method. It should be possible to rerun it for a different set of stations.
5        Things to think about
* Demand around a station is not even. More people may come from one side than another. Use that where the data allows.
* Buses that run short loops can charge at the station end. Think about where chargers sit relative to where routes end.
* More routes cover more area, but each gets fewer buses, so people wait longer. Balance reach against frequency.
* Traffic changes through the day. A route that takes 20 minutes at noon may take 35 at 6 pm.
* Avoid routes that only copy an existing bus service.
6        Data access
All datasets for this problem are shared through the Delhi Transport Stack platform. Register at delhi.transportstack.in and request access to the datasets you need. Bus schedules follow the GTFS Schedule standard and live positions follow GTFS Realtime.
Questions about the problems or data: csm@iiitd.ac.in.
Transport Stack Hackathon 2026  /  delhi.transportstack.in/hackathon
