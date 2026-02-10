---
layout: default
title: "My Worst Code Review (and Why I'm Grateful For It)"
categories: career teamwork codequality
---

Every developer has a code review story that still makes them cringe. This is mine. It happened early enough in my career that the lessons stuck permanently, and late enough that I really should have known better. Looking back, it was one of the most important moments in my growth as a developer, even though it felt terrible at the time.

## The Pull Request

I was about eight months into my first role writing application code after transitioning from test automation. I'd been working on an API endpoint that had some issues. The code was messy, the variable names were inconsistent, and there was a bug in the date parsing logic that was causing intermittent failures. A reasonable person would have fixed the bug, submitted a clean PR, and moved on.

I was not a reasonable person. I was a person who wanted to prove he belonged.

So I "refactored" the entire endpoint. I'm putting refactored in quotes because what I actually did was rewrite it to match my personal preferences. I renamed variables to what I thought was more readable. I extracted helper functions that only had one call site. I introduced a layer of abstraction that made the code "more flexible" for future requirements that nobody had asked for. I reorganized the file structure. I changed formatting that didn't match the rest of the codebase but matched what I liked. And somewhere in the middle of all that, I also fixed the actual bug.

The PR was over 500 lines of changes. The diff was a wall of red and green. If you were trying to find the bug fix, good luck. It was buried on line 340-something between a renamed variable and a new utility function that wrapped a single `Array.filter()` call.

```javascript
// My "improvement" - a utility function nobody asked for
const filterActiveUsers = (users) => {
  return users.filter((user) => user.status === 'active');
};

// What was already in the codebase and worked perfectly fine
const activeUsers = users.filter((u) => u.status === 'active');
```

I submitted the PR on a Friday afternoon (first mistake), gave it a description that said something like "Refactored user endpoint for better readability and fixed date parsing bug" (second mistake), and went home feeling pretty good about myself.

## The Feedback

Monday morning, I opened the PR and saw 30+ comments. My stomach dropped.

The senior developer on my team, let's call him Marcus, had gone through the entire thing. And to his credit, not a single comment was mean or dismissive. They were all genuine questions. But they were relentless.

"What problem does this abstraction solve?" "Why did you rename this variable? The existing name follows the convention used in the rest of the codebase." "This helper function is called once. What's the benefit of extracting it?" "Can you explain the reasoning behind this restructure?" And the one that stung the most: "I see there's a bug fix in here. Can you point me to which lines address the bug? It's hard to find in a PR this size."

He also left a longer comment at the top of the PR. It said something like: "I can see you put a lot of work into this, and I appreciate the effort to improve the codebase. But I'm having trouble reviewing it because there are several different changes mixed together. The bug fix, the renames, the abstractions, and the restructuring all need to be evaluated separately, and right now they're all tangled up. Could we break this into smaller PRs?"

There was also a comment on my clever abstraction layer. Marcus had written: "I've seen this pattern before. It looks like it adds flexibility, but in practice it adds indirection. Right now a new developer has to understand the abstraction to understand the code, and the abstraction doesn't do anything the direct code doesn't already do. Simpler is almost always better."

## My Initial Reaction

I was defensive. Immediately, completely defensive. I sat at my desk reading the comments and felt my face getting hot. I interpreted every question as an attack. "What problem does this solve?" felt like "You're an idiot." "Can you explain the reasoning?" felt like "There is no reasoning because you don't know what you're doing."

I drafted a response to every comment. Every single one was some version of "Well, actually..." I wanted to explain my thinking, justify every choice, and push back on the idea that my code wasn't an improvement. I was so focused on being right that I couldn't see what Marcus was actually telling me.

I'm grateful I didn't hit send on those responses. Instead, I went to lunch. I vented to a friend who wasn't a developer and therefore had no opinion on my abstraction layer. And somewhere between the sandwich and the walk back to the office, I started to hear the comments differently. Marcus wasn't saying I was a bad developer. He was saying the PR was hard to review. And honestly? He was right. If someone had submitted a 500-line PR to me and asked me to review it, I would have struggled too.

I went back to my desk, closed my drafted responses, and typed a much shorter reply: "You're right. I'll break this up. Sorry for the mess." Then I closed the PR and started over.

## What I Actually Learned

That code review taught me more about professional software development than any tutorial, course, or book I've ever read. Here's what stuck.

**Keep PRs small and focused.** A PR should do one thing. Fix a bug? That's a PR. Rename variables for consistency? That's a separate PR. Introduce an abstraction? Separate PR with a clear explanation of why. When you mix changes together, you make it impossible for the reviewer to evaluate each change on its merits. You also make it nearly impossible to revert one change without reverting everything. I broke my monster PR into four smaller ones. The bug fix was three lines and got approved in ten minutes.

**Don't mix refactors with bug fixes.** This is a specific case of the above, but it's important enough to call out separately. When a bug fix is buried in a refactor, it's invisible. Nobody can tell which lines fix the bug and which lines are cosmetic. If the refactor introduces a new bug, it's incredibly hard to isolate. And if you need to hotfix something in production, you want the smallest possible change, not a 500-line rewrite.

**Abstractions need to earn their place.** I was creating abstractions preemptively, for flexibility that might never be needed. Every abstraction adds a layer of indirection that someone has to understand. That cost is only worth paying if the abstraction solves a real, current problem. "We might need this later" is almost never a good reason to add complexity now. YAGNI (You Aren't Gonna Need It) is a cliche because it's true.

**Clever code is the enemy of readable code.** I wanted to impress people. I wanted them to look at my code and think, "Wow, this person really knows what they're doing." But the best code doesn't make people think that. The best code makes people think nothing at all. They read it, they understand it, they move on. Boring code is good code. Code that makes you feel smart when you write it will make someone else feel stupid when they read it, and that someone might be you in six months.

**Your code style preferences are just preferences.** I renamed variables because I thought my names were better. But "better" is subjective, and consistency across a codebase is more important than any one person's preferences. If the codebase uses `u` for user in short lambdas, don't change it to `user` just because you like it more. Match the existing patterns.

## How I Give Code Reviews Now

That experience fundamentally changed how I approach code reviews, both giving and receiving them. Here's what I try to do.

**I ask questions instead of making demands.** Instead of "This should be a separate function," I write "What do you think about extracting this into its own function? It might make the intent clearer." The difference is subtle but it matters. Questions invite collaboration. Demands create resistance. Sometimes the author has context I don't, and the question gives them space to share it.

**I focus on "what" not "how."** If something needs to change, I try to explain what the problem is rather than prescribing exactly how to fix it. "This might be hard to test because it depends on the current time" is better than "Use dependency injection for the date." The author usually knows their code better than I do and can find a solution that fits.

**I always find something positive to say.** This isn't about being fake or sugarcoating. It's about acknowledging that someone put work into this and that there are good things in the PR. "Nice approach to the error handling here" or "Good call using a Map instead of an Object for this" takes five seconds to write and makes the whole review feel collaborative instead of adversarial.

**I separate the important from the nitpicks.** Not every comment is equally important. I prefix minor suggestions with "Nit:" or "Minor:" so the author knows they can take it or leave it. The things that actually matter, correctness issues, security concerns, maintainability problems, get their own clear comments with explanations of why they matter.

**I remember what it felt like.** Every time I'm about to leave a blunt comment, I think about sitting at my desk reading Marcus's 30+ comments and how it felt. I don't soften my feedback to the point of uselessness, but I try to write every comment as if I'm talking to someone who's trying their best. Because they are.

Marcus, if you ever read this: thanks. I didn't appreciate it at the time, but that review made me a better developer and a better teammate. I owe you one.
