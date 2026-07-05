# Reddit Data API access request

As of late 2025, Reddit's [Responsible Builder Policy][rbp] requires **manual
approval for any new API OAuth token**. Self-serve script-app creation at
`https://www.reddit.com/prefs/apps` now dead-ends: the "create app" captcha
reloads indefinitely and links back to the policy. This is a Reddit-side gate,
not a client, network, or account-verification problem.

Community reports (r/redditdev, r/help) indicate non-commercial / hobby
requests are **frequently not approved** — the clearest approvals have been
moderator tools. Treat this as best-effort; the digest is designed to run
without Reddit (`reddit_enabled = false`), so approval is not on the critical
path.

## Where to submit

Reddit developer-clone request ticket form:

<https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164&tf_42139884615700=api_request_type_developer_clone>

Requirements before submitting:

- Reddit account with a **verified email**.
- You must agree to the [Developer Terms][devterms] and the
  [Data API Terms][dataterms].

## Ticket form answers

The developer-clone form asks six questions. Answers below. Keep them truthful —
the policy explicitly prohibits misrepresenting how or why you access Reddit
data — and note this app is *read-only consumption*, which is the category most
likely to be rejected. Lead with "does no harm, low volume, links back" rather
than inventing a benefit.

**1. What benefit/purpose will the bot/app have for Redditors?**

> It's a personal, read-only tool, so I'll be candid: it provides no direct
> on-platform benefit to other Redditors — it never posts, comments, votes, or
> messages. Its purpose is to me: a once-daily private email digest of Formula 1
> / IndyCar news. The indirect benefit to Reddit is that when a Reddit
> discussion ranks highly, the digest links back to the thread's permalink,
> driving me (and anyone I later share it with) back to Reddit to read and
> participate. It imposes near-zero load (a handful of read calls per day) and
> takes no action that could spam, manipulate, or degrade any community.

**2. Detailed description of what the Bot/App will be doing on the Reddit
platform.**

> Strictly read-only, application-only (script) OAuth via PRAW. Once per day a
> cron job runs and, for each configured subreddit, calls the equivalent of
> `subreddit.top(time_filter="day", limit=50)`. From each returned submission it
> reads only: title, external URL, score, comment count, and permalink. Nothing
> is written back — no posts, comments, votes, saves, subscriptions, DMs, or
> profile changes.
>
> How the data is used: the app independently gathers motorsport news from
> public RSS feeds (Autosport, The Race, Motorsport.com, RACER) and the GDELT
> news API. It clusters stories across those sources, and uses the Reddit score
> + comment count as one popularity signal (~50% weight) to rank which stories
> are "buzzing." The top ~8 are summarized and emailed to me.
>
> Concrete example: if r/formula1's top-of-day post links to an Autosport
> article about a driver signing, and that same story also appears in my
> RSS/GDELT pull, the Reddit engagement numbers boost that story's rank in my
> digest, and the digest includes a link back to the Reddit thread. Total volume
> is roughly a dozen API calls/day, well under the 100 QPM free tier. No data is
> retained beyond that day's ranking; nothing is redistributed, sold, or used to
> train models.

**3. What is missing from Devvit that prevents building on that platform?**

> Devvit hosts apps that run inside Reddit — triggered by Reddit events, rendered
> in Reddit's UI (posts, menu actions, custom post types), acting on the
> subreddit where they're installed. This app is the opposite shape: a standalone
> external consumer. It runs as an independent scheduled process on my own
> server, its primary data sources are non-Reddit (RSS feeds + the GDELT news
> API), and its only output is an email to my inbox — there is no in-Reddit
> surface for Devvit to render and no subreddit-side action for it to perform.
> Reddit is one read-only input among several, aggregated off-platform. Devvit
> has no model for "external cron job that reads public data from a few
> subreddits and combines it with outside sources," so there's nothing for it to
> host.

**4. What subreddits do you intend to use the bot/app in?**

> r/formula1 and r/IndyCar (read-only). Possibly other motorsport subreddits
> later, but these two to start.

**5. Username you will operate this Bot/App under (optional):**

> u/andyjs55

**6. Attachments (optional):**

> Leave blank, or offer the project repo/code to verify the read-only claim if
> asked.

## If approved

Set the issued credentials as env vars (see `.env.example`) and flip
`reddit_enabled = true` in `config.toml`:

```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=motorsports-digest/1.0 by u/yourusername
```

Verify with `python -m digest.main --dry-run` — you should see Reddit items in
the ranked pool instead of the `[reddit] ... skipping` line.

[rbp]: https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy
[devterms]: https://redditinc.com/policies/developer-terms
[dataterms]: https://redditinc.com/policies/data-api-terms
