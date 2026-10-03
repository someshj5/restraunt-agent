from app.agent.runner import run_agent


response = run_agent(
    "Book a table for 4 people tomorrow at 11:00 PM outside."
)

print("\nFINAL RESPONSE:")
print(response)

print("2nd run...")
response = run_agent(
    "Book a table for 4 people today at 11:00 PM outside."
)

print("\nFINAL RESPONSE:")
print(response)