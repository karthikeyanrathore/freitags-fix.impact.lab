We need to build a prototype that we can demo of our product within a few hours.  
Requirements: we run a pizza business with a website built by a third party vendor (this will be mocked by you). We need it to be available without disruption, all ‘add’ buttons must register, the latency must be low. We want to demo the website working and then erroring.

For our demo: we need an artifact that demonstrates the failure pattern. We would want the telemetry or failed tests sent to have an agent pick up, diagnose, and resolve.

We want an agent to pick up the issue, investigate, suggest a resolution and implement the fix. What can we build to demonstrate the agent loop in the process. 

The business owner does not need to be involved, but gets the history of the work of the agent and the resolution.

We want to build this using git and vercel, but can also use other applications to demo.

Demo:

- Website not responding with 429 error (we can also use 503, 504\)  
- The agent get the failure alert   
- The agent runs the diagnostics, identifies the fix and implements the change. We still need version control to have the history  
- The fix is implemented by the agent and tested again  
- The website is working and displays our pizza website without errors  
- Message sent with a digest of the fixes  
- The business owner is happy with the results and gains a greater appreciation for AI usage