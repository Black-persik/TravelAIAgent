# Task: hackathon track "O!дин запрос" (Ostrovok)

A summary of the hackathon brief in our own words. It is the reference for what the agent must do; `docs/ARCHITECTURE.md` describes how.

## Problem
People rarely plan a trip in one go. They collect ideas on social media, pick a destination in one tab, a hotel in another, tickets in a third and reviews in a fourth, then cross-check everything by hand: do the dates match, will they make check-in, does the transfer eat the hotel savings.

Classic search needs exact parameters (city, dates, guests). It cannot handle a request like "somewhere warm by the sea in November, not expensive, with a child, no long flights", so the user has to turn it into a plan themselves, and many give up at that step.

## Goal
Build a prototype AI agent for Ostrovok that turns one traveller message into a ready trip plan and guides the user through every stage: **inspiration → destination choice → search → comparison → trip assembly → purchase**.

The agent must act, not chat: clarify, search, compare, rebuild the plan and finish the task. An agent that only retells search results in a chat does not count as a solution. Each stage should be noticeably better than ordinary search.

## Constraints
- Ostrovok provides no API, MCP servers or data. Data sources, tools, logic and UI are ours.
- Open APIs, public datasets and synthetic data are allowed. Mocked data must be disclosed honestly in the demo.
- Payment and booking only need to be simulated.
- Free choice of models, technologies and architecture.

## User stories
- **Traveller:** describe the trip in my own words and get a clear plan with options, without spending an evening across ten tabs, and be confident in the choice.
- **Ostrovok:** users go from idea to purchase inside the service and buy the whole trip, which raises conversion, average order value and retention.
- **Hotel:** be recommended to guests it really suits, so there are fewer cancellations and disappointed reviews.

## Core requirements
1. **Understanding and clarification.** Extract explicit and hidden requirements (budget, travellers, constraints, trip mood). Ask only the questions without which the agent cannot proceed. A 15-question form is not acceptable.
2. **Inspiration and destination choice.** If the user does not know where to go, suggest destinations and explain each: why it fits, how much it costs, what the weather is like, how long the journey takes.
3. **Search and comparison.** Find and compare hotels, flights or trains, and transfers, not only by price but by what matters to this user: cancellation terms, meals, location, travel time, date and time compatibility.
4. **Explaining the choice.** For each recommendation: why it fits, what was sacrificed, what the risks are. The user must understand the agent's logic and be able to correct it.
5. **Trip assembly and purchase.** Combine the chosen items into one plan and cart, check the connections (arrival, check-in, transfer) and take the user to a (simulated) checkout.
6. **Replanning.** When conditions change ("two days later?", "smaller budget", "our dog is coming"), rebuild the plan instead of starting the search from scratch.

## Optional requirements
- Post-purchase support: early check-in request, date changes, reminders, a transfer for an already booked hotel.
- Memory and personalisation: remember user preferences across sessions.
- Agent quality metrics: our own test set and measurements (share of scenarios completed end to end, number of clarifying questions, time to first recommendation, connection errors).
- Mobile version or a messenger bot.

## Evaluation
A working prototype in which the whole path from the first message to a (simulated) purchase can be completed. At the defence, the jury gives the agent requests the team has not seen before, so robustness to unseen phrasing matters more than polish on prepared scenarios.
