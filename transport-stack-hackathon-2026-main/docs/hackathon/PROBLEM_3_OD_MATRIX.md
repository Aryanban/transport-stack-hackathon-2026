# PROBLEM 3 OD MATRIX

﻿Problem 3 / Phase 2
Origin–destination matrix for Delhi public transit
Phase
	Phase 2, for shortlisted teams
	Core data
	Bus e-ticketing data (3–4% of bus tickets), metro entry and exit gate data, static GTFS
	You build
	A city-wide origin-destination (OD) matrix for public transit, with a documented extrapolation method
	Judged on
	Consistency with known ridership and metro counts, and the soundness of the scaling method
	1        Background
To plan routes and set frequencies, a city needs to know where trips start and where they end. This is captured in an origin-destination (OD) matrix. It is a table. Each row is a place where trips start. Each column is a place where trips end. Each cell says how many trips go from one to the other.
Delhi has two partial views of this. Bus e-ticketing data records the start and end of each trip, but covers only about 3-4% of total bus tickets. Metro gate data is far more complete. Almost every metro trip is recorded when the passenger enters and leaves a station. Neither source alone gives the full picture.
2        The challenge
Estimate an OD matrix for Delhi’s public transit that matches real travel as closely as possible. The core problem is scaling up. You must turn a small bus e-ticketing sample into an estimate of all bus trips. Use the much richer metro data to understand how travel is spread across the city.
2.1        What the system should do
* Produce an OD matrix at stop or zone level. A zone is an area that groups nearby stops.
* Produce separate matrices for different times of day, at least peak and off-peak.
* Scale the bus sample up to total bus ridership. Correct for the fact that e-ticket users may not be typical riders.
* Combine bus and metro trips into one picture of public-transit travel.
* Where possible, show trips that use both bus and metro, such as a bus ride to a metro station.
2.2        An example
Take two zones: one around Rajouri Garden and one around Nehru Place. Your matrix should say roughly how many people travel from the first to the second by bus, by metro and by both, between 8 and 10 am on a weekday. It should also say how sure you are of that number.
2.3        Scope
Bus and metro. You decide the zones. Options include a hexagonal grid, census wards. Explain why you chose them. Smaller zones show more detail but have fewer trips per cell, so they are less reliable.
3        Data provided
3.1        Bus e-ticketing data
Ticket records with boarding and alighting stops, times, route and fare. They cover about 3–4% of all bus tickets. Exact schema and period (to be confirmed).
3.2        Metro entry and exit gate data
Counts or records of passengers entering and leaving each metro station, by time. Level of detail, and whether trip-level start and end pairs are included - from transport stack.
3.3        Supporting data
Static GTFS for bus stops and routes. Total daily bus ridership figures for scaling (you can use estimates from annual reports of DTC). You may add public data such as population or land use. Document every source you add.
4        Expected deliverables
* The OD matrix in an open format, CSV or Parquet, with a file defining your zones (GeoJSON).
* Code that rebuilds the matrix from the raw data.
* A short technical note. Explain how you scaled up the sample, what you assumed, and where you are least sure.
* Maps and charts, such as lines between zones drawn by trip volume, and the busiest OD pairs by time of day.
* Checks of your matrix. Do row and column totals match known boardings and ridership? Do metro trips match station entry and exit counts?
5        Things to think about
* E-ticket users may not be a random sample of riders. Their share may change by route, area or time of day. If you ignore this, your matrix will be skewed.
* A ticket records one bus ride, not a whole journey. A person who changes buses buys two tickets.
* Metro data tells you a lot about where people go. It does not tell you how they reached the station.
* Many cells in the matrix will be empty or tiny. Decide how to handle them.
* Give a range, not just a number, for the major flows.
6        Data access
All datasets for this problem are shared through the Delhi Transport Stack platform. Register at delhi.transportstack.in and request access to the datasets you need. Bus schedules follow the GTFS Schedule standard and live positions follow GTFS Realtime.
Questions about the problems or data: csm@iiitd.ac.in.
Transport Stack Hackathon 2026  /  delhi.transportstack.in/hackathon
