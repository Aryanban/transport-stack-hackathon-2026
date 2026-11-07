# PROBLEM 5 METRO BUS CROWDING

﻿Problem 5 / Phase 2
Metro and bus crowding estimation
Phase
	Phase 2, for shortlisted teams
	Core data
	About one month of AFC boarding and alighting data for metro and bus, static GTFS
	You build
	Load estimates by line or route, segment and time of day
	Judged on
	A sound method for turning taps into on-board load, checked against known peak patterns
	1        Background
Automatic Fare Collection (AFC) systems record each time a passenger taps a card or token. On the metro, people tap in at the station where they start and tap out where they finish. On buses, they tap when they board, and sometimes when they get off.
Over a month, these taps show how the number of people on board rises and falls along each metro line and bus route. This number is called the load. Operators can use it to decide where to add trains or buses. Commuters can use it to avoid the most crowded trips.
2        The challenge
Estimate how crowded Delhi’s metro and buses are, using one month of AFC data. Give the load on each stretch of each line or route, in each direction, at each time of day.
2.1        What the system should do
* Estimate the load on each segment, meaning the stretch between two stations or stops next to each other. Do this by direction and by time of day.
* Turn load into a crowding level, using the capacity of the train or bus.
* Make the results easy to query and see. For example, a chart of load along each line, and a heatmap of crowding across the day.
2.2        An example
Take the Blue Line between Rajiv Chowk and Noida. Your output should show, for each segment and each half hour of a weekday, how many people are on board and how full the trains are. It should show which segments are the most crowded in the morning peak, and that the busiest direction flips in the evening.
2.3        Who would use this
Metro and bus operators, to see where and when they run out of space and where extra trains or buses would help most based on the observed demand. Commuters, to choose a less crowded time or route. Planners, to see which corridors need new capacity. Build your outputs so these groups can read them without help.
2.4        How it differs from Problem 2
Problem 2 is about bus crowding inside a journey planner, using ticket sales. This problem covers both metro and bus, uses tap-in and tap-out data, and focuses on how good the load estimate is. Teams moving on from Problem 2 can build on their earlier work.
3        Data provided
3.1        Metro entry/ exit/ footfall data
The data can be accessed on the delhi.transportstack.in platform.
3.2        Network information
Metro line and station sequences (to be confirmed), and static GTFS for bus routes and stops. Capacities of buses and trains (to be confirmed).
4        Expected deliverables
* Load estimates for each segment, by direction and time of day, in an open format such as CSV or Parquet.
* A query tool or a set of charts and maps.
* A short list of the most crowded segments and times on the metro and on buses, with the load and crowding level for each.
* Code that rebuilds the estimates from the raw AFC data.
* A short technical note. Explain how you turn taps into the number of people on board. Explain how you decide which path a metro passenger took when more than one was possible.
* Checks of your results. Do the loads match station entry and exit totals? Do they show the peaks and busy corridors that are already well known?
5        Things to think about
* On the metro, a trip between two stations may use more than one line. Say how you assign such trips to lines.
* Bus tap-outs may be missing. Say what you do when you know where a person boarded but not where they got off.
* A tap tells you when a person entered the station, not which train they took.
* Load depends on frequency. The same flow of people is more crowded on a service that runs less often.
* Some passengers pay by other means and do not appear in AFC data. Say how this affects your estimates.
* Weekdays and weekends behave differently. So do holidays and days with events.
6        Data access
All datasets for this problem are shared through the Delhi Transport Stack platform. Register at delhi.transportstack.in and request access to the datasets you need. Bus schedules follow the GTFS Schedule standard and live positions follow GTFS Realtime.
Questions about the problems or data: csm@iiitd.ac.in.
Transport Stack Hackathon 2026  /  delhi.transportstack.in/hackathon
