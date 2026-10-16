# Vast Take-Home Coding Challenge

## Objective

You are tasked with developing a simulation for a lunar Helium-3 space mining operation. This simulation will manage and track the efficiency of mining trucks and unload stations over a continuous 72-hour operation.

## Key Components

* **Mining Trucks:** These vehicles perform the actual mining tasks.
* **Mining Sites:** Locations on the moon where the trucks extract Helium-3. Assume an infinite number of sites, ensuring trucks always have access to mine without waiting.
* **Mining Unload Stations:** Designated stations where trucks unload the mined Helium-3. Each station can handle one truck at a time.

## Operation Details

* There are (n) mining trucks and (m) mining unload stations.
* Mining trucks can spend a random integer duration between 1 to 5 hours mining at the sites (1 hour resolution).
* It takes a mining truck 30 minutes to travel between a mining site and an unload station.
* All trucks are empty starting at a mining site when the simulation begins.
* Unloading the mined Helium-3 at a station takes a random integer duration between 30 and 60 minutes (1 minute resolution).
* Trucks are assigned to the first available unload station. If all stations are occupied, trucks queue at the station with the shortest wait time and remain in their chosen queue until unloaded.
* Mining trucks, mining unload stations, and simulation time should be parameterized and configurable.

## Simulation Requirements

* The simulation must be configurable to accommodate various numbers of mining trucks (n) and unload stations (m).
* Calculate and report statistics for the performance and efficiency of each mining truck and unload station.
* The simulation represents 72 hours of non-stop mining and must execute faster than real-time to provide timely analysis.

## Language and Programming Paradigms

Please implement this project in **Python**. Please leverage **OOP** where it is appropriate.

## Goal of the Exercise

The primary goal of this challenge is to demonstrate your ability as a software engineer. This process is designed to mimic a real-world scenario, including design, implementation, and design review. You will be evaluated based on various skills, including but not limited to:

1. **Communication:** Clear and concise explanations of your code and design.
2. **Documentation:** Providing well-documented code and explanations.
3. **Code Cleanliness:** Writing clean and organized code.
4. **Code Deployment:** Demonstrating your ability to deploy and manage code.

Organize and set up your code in the repository as you would for production-ready software. The use of generative AI and coding tools is allowed, but it is expected that you thoroughly understand the code you have submitted. **Do NOT use any third-party simulation library.**

Include a summary report showing all statistics for the execution where there are **n=10 mining trucks**, **m=3 unloading stations**, and a **simulation time of 72 hours**, in your repository.

## How to Submit

Submit your code and any accompanying content, such as data or results, using GitHub or Bitbucket, set to public viewing. Please email us a link to your submitted code when you are ready for us to review it.

## Questions

Please feel free to ask any clarifying questions about this assignment via email with your recruiter.
