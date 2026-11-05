# Claude plan terms: questions for the organization

Read this before Amber data goes into any AI tool, or when a user asks "are we allowed to put this in Claude?"

**This is not legal advice, and you don't interpret the answers.** Whether the org may use a kind of data with an AI tool is the org's decision, made by whoever owns its data policy, based on its own plan's terms. Your job is to help them ask the right questions and record what they decided.

## Contents
1. How to use this
2. The questions
3. Recording the decision

## 1. How to use this

Offer the checklist as a short list the user can take to their data policy owner (or whoever manages the org's Claude account). Don't answer the questions yourself from general knowledge about Claude plans: terms differ between plans and change over time, and the answer that counts is the one in the org's own agreement and settings.

Say something like:

> Before we use donor or staff details here, it's worth checking your organization's Claude plan terms. Here are six questions your data policy owner can answer from your plan's documentation or account settings. I can't answer them for you, because they depend on your specific plan.

## 2. The questions

1. **Which Claude plan does the organization use** (and is this the org's account, or someone's personal one)?
2. **Is content from conversations and uploaded files used to train models** under that plan, and is there a setting that controls it? Who checked, and when?
3. **How long is conversation and file content kept**, and can it be deleted?
4. **Who in the organization can see shared projects, chats or files** created with this account?
5. **Does the organization have its own policy** on which data may go into AI tools (for example, "no client data in any AI tool")? If it does, that policy wins over anything this skill says.
6. **Do any funders, contracts or partners restrict** how the org may handle certain data, such as program data shared under an agreement?

## 3. Recording the decision

Ask the user to note in their state file (`pii-guard-{slug}.json`, under `plan_terms`):

- who answered, and when
- what was decided ("Amber data allowed after pii-guard redaction", "no named data at all", …)
- where the source is (a policy document, an account settings page), **not** a copy of the terms

If nobody can answer yet, carry on with Green data only and leave the item open as `[NEEDS FROM ORG: plan-terms decision]`.
