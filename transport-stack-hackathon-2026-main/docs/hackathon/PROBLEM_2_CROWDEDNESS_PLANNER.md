# PROBLEM 2 CROWDEDNESS PLANNER

﻿Problem 2 / Phase 1
Crowdedness-aware journey planner
Phase
	Phase 1, open to all registered teams
	Core data
	4–5 weeks of e-ticketing and ETM ticket data, static GTFS
	You build
	A crowdedness model by route and time of day, and a journey planner that shows it
	Judged on
	How well the crowding estimate is grounded in the data, and how clearly it is shown to commuters
	1        Background
How crowded a bus is matters to a commuter as much as how long the trip takes. A packed bus is slow to board, hard to stand in, and often skipped by people who can choose another. Yet journey planners rank options only by time and number of changes.
Delhi records every bus ticket it sells. Most tickets come from the conductor’s Electronic Ticketing Machine (ETM). Some come from e-ticketing through an app or QR code. Each record says where and when a person got on, and usually where they planned to get off. Together, these records show how full each bus is along its route.
2        The challenge
Use about 4–5 weeks of ticket data to estimate how crowded buses are, by route and time of day. Then add this to a journey planner, so that a commuter can compare options on both travel time and crowding.
2.1        What the system should do
* Turn ticket records into an estimate of how many people are on board. Do this by route, direction, stretch between stops, and time of day.
* Turn that number into a crowding level a commuter understands, such as seats available, standing room or crowded.
* Show the crowding level next to each journey option in a planner.
* Let the user choose between a faster trip and a more comfortable one.
2.2        An example
A user asks: from Anand Vihar to Connaught Place, leaving at 6 pm on a weekday. The planner shows three options. The fastest takes 45 minutes but the bus is usually crowded on the middle stretch. A second option takes 55 minutes and usually has standing room. A third, leaving 20 minutes later, has seats. The user can see this at a glance and pick.
2.3        Who would use this
Commuters, to pick a trip they can bear. Bus operators and planners, to see which routes and hours are overloaded and where extra buses would help most. Build your outputs so both groups can read them.
2.4        Scope
Bus only. Teams build their own journey planner on static GTFS. The crowding model is the main contribution. A simple planner with a sound crowding model is better than a polished planner with a weak one.
3        Data provided
3.1        Ticketing data (ETM and e-ticketing)
About 4–5 weeks of ticket sales from conductors’ ETMs and from e-ticketing. Each record gives the time of sale, the route, the bus, the boarding stop, the alighting stop (or fare stage) and the fare. A fare stage is a group of stops that share a fare. The final schema (to be confirmed).
3.2        Route and stop information
The static GTFS feed, the standard format for transit schedules. It gives stop locations, the order of stops on each route, and the scheduled trips.
3.3        What the data covers
Four to five weeks is enough to see regular weekly patterns. It is not enough to see seasons, festivals or the monsoon. Check how your estimates hold up from one week to the next.
4        Expected deliverables
* A pipeline that turns raw ticket records into crowding estimates. Someone else should be able to rerun it.
* Crowding outputs that can be queried or shown on a map, by route, stretch and time of day.
* A journey planner or demo screen that shows crowding next to each route option and its travel time.
* A short technical note. Explain your method and your assumptions. Say where your estimates are least reliable.
* Some checks against known patterns. For example, morning and evening peaks, busy corridors, and weekday versus weekend.
5        Things to think about
* A ticket tells you where a person got on and often where they got off. To know how many are on board, you need to group tickets by bus trip and keep a running count.
* Some riders do not appear in ticket data, such as pass holders. Decide how to account for them, and say how.
* The ticket says where a person planned to get off. They may get off earlier or later.
* Bus size matters. A load of 60 means different things on a 12 m and a 9 m bus.
* Some routes and hours have few tickets. Say how much you trust your estimate there.
* Keep the crowding display simple. A commuter should understand it in a second.
6        Data access
All datasets for this problem are shared through the Delhi Transport Stack platform. Register at delhi.transportstack.in and request access to the datasets you need. Bus schedules follow the GTFS Schedule standard and live positions follow GTFS Realtime.
Questions about the problems or data: csm@iiitd.ac.in.
Transport Stack Hackathon 2026  /  delhi.transportstack.in/hackathon
