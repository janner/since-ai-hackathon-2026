# Kaista through the user's eyes

This page is for the Traficom frequency specialist. Five steps, no command line.

**Before you start.** The tool opens in a browser. The service fetches the new BR IFIC package from
ITU every two weeks, so you do not bring the file yourself. The "Check now" button in the top bar
asks ITU right away (the same check from a command line is `python scripts/monitor.py --check`). If
the automatic fetch does not work, the developer runs the pipeline by hand
(`python -m app.pipeline --ific <mdb>`); the page has no file upload.

## Five steps

1. **Open the address in a browser.** The top bar shows the funnel numbers and the queue length.
   The "Funnel" column on the left says how many notices were screened and why the rest dropped out.
   Click any funnel row and the queue filters to it: a stage row shows the notices that reached that
   stage, a class row narrows to that class, and a Drops row shows the notices dropped for that
   reason. The same row again, or "Show all", restores everything.
2. **Check for new material.** The service fetches the new BR IFIC package from ITU itself; you do
   not bring the file. The "Check now" button in the top bar says whether there is a new package and
   runs it. The register and M4 do not change with every package, so they live on the server.
3. **Look at the queue.** The queue lists every notice in three sections: "Needs attention",
   "Checked, nothing to note" and "No effect on Finland". The ones that need attention come first.
   The queue orders by regulatory stage first: "Advance publication" and "Coordination request" come
   before "Recorded in the MIFR", because those can still be influenced. Inside a stage the order is
   "Exceeds limit", "Near limit", "No satellite use in Finland" (a band with no satellite use in
   Finland) and "Cannot decide". The margin does not order the queue.
4. **Open a case.** Read "What this means" and "What information is missing". The calculation sits
   behind "Show calculation"; open it if you want to check the number yourself.
5. **Copy the question** from "Question to the other administration" into your own message.

## What the tool does not do

The tool makes no decision: every number comes from code, not from a language model. It does not
send a letter for you; it gives you a draft that you read and send. It also does not record what you
have looked at: no "seen" mark, no comments, no owners.
