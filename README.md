# Kessler

## Inspiration
Our inspiration comes from the Kessler syndrome, the theoretical scenario where the density of objects in low Earth orbit (LEO) is high enough that collisions between objects could cause a cascade, generating hundreds or thousands of high-speed fragments and making space exploration and satellite operations increasingly hazardous. As orbital congestion grows, automated, rigorous, and transparent safety tools are essential to protect the future of spaceflight.

## What is does
Our inspiration comes from the Kessler syndrome, the theoretical scenario where the density of objects in low Earth orbit (LEO) is high enough that collisions between objects could cause a cascade, generating hundreds or thousands of high-speed fragments and making space exploration and satellite operations increasingly hazardous. As orbital congestion grows, automated, rigorous, and transparent safety tools are essential to protect the future of spaceflight.

- It ingests live public orbital and encounter data (CelesTrak and SOCRATES).
- It refines close-approach predictions and optimizes hypothetical avoidance maneuvers.
- It screens for secondary conjunction risks to ensure maneuvers don't create new hazards elsewhere.
- It models atmospheric decay and persistence while estimating covariance-based collision probabilities. Finally, it presents all of this through an interactive 3D orbital globe and structured workflow for - decision support.

## How we built it
- Backend: Built with Python 3.12+ and FastAPI. It handles orbital propagation via SGP4, numerical integration using DOP853 (via Astropy), collision-probability calculations with SciPy quadrature, atmospheric density modeling through NRLMSIS 2.1 (via pymsis), and precise reference frame transforms via Astropy.
- Frontend: Built with React 19, TypeScript, and Vite. It utilizes Three.js to render an immersive 3D orbital workspace and communicates with the FastAPI backend via clean REST API endpoints.
- Testing & Deployment: Validated thoroughly using pytest and benchmarked via actual-machine timing. The backend deploys serverlessly to Modal, while the static frontend is hosted on Vercel (not currently implemented yet).

## Challenges we ran into 
Some challenges we ran into were translating those complex orbital mechanics such as precise covariance transformations, numerical integration, and atmospheric density variations into high-performance, reliable backend code. We had to carefully tune and validate all data against gold-standard references. The next challenge with this was managing the data, specifically being bridging live public datasets (CelesTrak/SOCRATES) with the front end. We need multi-step pipelines (encounter detection --> maneuver optimization --> secondary screening), which required a robust architecture to handle everything cleanly without slowing down the user experience.

## Accomplishments that we're proud of 
Some accomplishments we are proud of are how the project goes far beyond simple tracking, handling everything from public catalog ingestion and encounter detection to maneuver optimization, secondary screening, and browser-based visualization. The backend also explicitly leverages live CelesTrak and SOCRATES data with fully documented checkpoint results, avoiding synthetic-only shortcuts. On top of that, we integrated drag-based persistence analysis, giving a deeper physical simulation than a standard Keplerian orbit viewer. 

## What we learned 
Building Kessler deepened our appreciation for the intersection of rigorous space physics and modern web engineering. We learned how to handle high-precision scientific libraries (like Astropy and SciPy) inside a production web API, optimize computational workflows for real-time responsiveness, and design practical UI/UX interfaces for complex scientific data. 

## What's next for Kessler 
Expanding support for advanced maneuver planning. Adding multi-satellite constellation collision monitoring dashboards. Integrating automated alert webhooks for real-time conjunction warnings Optimize the UI more and make the elements better and more user friendly.