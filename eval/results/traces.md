# Plans and their traces

From the eval run of 2026-10-15 20:03 UTC (`latest.json`). Member: the fictional Jordan.

## deadlift

> Full body 40 min, no deadlifts.

8 exercises, 30.7 min, 5001 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | - | - |
| Dumbbell Hip Thrust | 3 | fits a priority-1 goal; uses equipment the member prefers | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers | - |
| Glute Bridge | 3 | fits a priority-1 goal | same pattern trained in the last two days |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers | - |
| Alternating Low Plank To Low Side Plank | 3 | - | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers | - |
| Ground Upper Trap Stretch | 1 | - | - |

**Request read:** deadlifts -> Deadlift (accepted, exact); full body -> full body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Excluded by request (Deadlift): 2 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Journey-stage rule (programming.yaml, not yet signed) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the safe exercises available can't fill 40 minutes at 2 sets.
- Planned 31 of 40 minutes: not enough safe exercises to fill the time.

## left-knee

> 45 minutes, lower body. Her left knee is still a bit sore.

9 exercises, 35.0 min, 3474 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | - | - |
| Dumbbell Hip Thrust | 3 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers | same pattern trained in the last two days |
| Glute Bridge | 3 | matches the requested focus; fits a priority-1 goal | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 3 | - | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers | - |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers | - |
| Bodyweight Pike | 3 | - | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers | - |
| Ground Upper Trap Stretch | 1 | - | - |

**Request read:** knee -> Knee (left) (accepted, exact); lower body -> lower body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml, not yet signed) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the safe exercises available can't fill 45 minutes at 2 sets.
- Planned 35 of 45 minutes: not enough safe exercises to fill the time.

## no-barbell

> 30 min upper body. She has no barbell and no bench this week.

7 exercises, 24.4 min, 2147 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | stands in for Bench-Supported Incline YTI, which needs equipment the member lacks | - |
| Alternating Dumbbell Overhead Press | 3 | matches the requested focus; uses equipment the member prefers | - |
| Push-Up to Knee-Drive | 3 | matches the requested focus; stands in for Alternating Dumbbell Decline Bench Press, which needs equipment the member lacks | - |
| Resistance Band Reverse Curl | 3 | matches the requested focus; stands in for Single-Arm Dumbbell Preacher Curl, which needs equipment the member lacks | - |
| Alternating Low Plank To Low Side Plank | 3 | - | - |
| Glute Bridge | 3 | fits a priority-1 goal | same pattern trained in the last two days |
| Ground Upper Trap Stretch | 1 | - | - |

**Request read:** barbell -> Barbell (accepted, exact); bench -> nothing (no_match, none); upper body -> upper body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 34 exercises

**Equivalent alternatives:** Push-Up to Knee-Drive instead of Alternating Dumbbell Decline Bench Press; Push-Up to Knee-Drive instead of Barbell Decline Bench Press; Standing Neck Circles instead of Bench-Supported Incline YTI; Push-Up to Knee-Drive instead of Dumbbell Incline Chest Fly; Push-Up to Knee-Drive instead of Dumbbell Neutral-Grip Bench Press; Resistance Band Reverse Curl instead of Single-Arm Dumbbell Preacher Curl

**Notes:**
- "bench" was read as every matching item: Adjustable Bench - Decline, Adjustable Bench - Incline, Flat Bench, Preacher Curl Bench.
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml, not yet signed) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the safe exercises available can't fill 30 minutes at 2 sets.
- Planned 24 of 30 minutes: not enough safe exercises to fill the time.

## no-dumbbells

> Upper body, 30 minutes, she left her dumbbells at the office.

7 exercises, 24.4 min, 2283 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | - | - |
| Push-Up to Knee-Drive | 3 | matches the requested focus; stands in for Alternating Dumbbell Decline Bench Press, which needs equipment the member lacks | - |
| Resistance Band Reverse Curl | 3 | matches the requested focus; stands in for Single-Arm Dumbbell Preacher Curl, which needs equipment the member lacks | - |
| Alternating Low Plank To Low Side Plank | 3 | - | - |
| Glute Bridge | 3 | fits a priority-1 goal; stands in for Dumbbell Hip Thrust, which needs equipment the member lacks | same pattern trained in the last two days |
| Bodyweight Pike | 3 | - | - |
| Ground Upper Trap Stretch | 1 | - | - |

**Request read:** dumbbells -> Dumbbell (accepted, exact); Upper body -> upper body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 37 exercises

**Equivalent alternatives:** Push-Up to Knee-Drive instead of Alternating Dumbbell Decline Bench Press; Push-Up to Knee-Drive instead of Dumbbell Incline Chest Fly; Push-Up to Knee-Drive instead of Dumbbell Neutral-Grip Bench Press; Resistance Band Reverse Curl instead of Single-Arm Dumbbell Preacher Curl; Glute Bridge instead of Dumbbell Hip Thrust

**Notes:**
- Left out 1 exercise(s) the member says they dislike: Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml, not yet signed) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the safe exercises available can't fill 30 minutes at 2 sets.
- Planned 24 of 30 minutes: not enough safe exercises to fill the time.

## no-match-focus

> Explosive plyometric jump training, 30 minutes.

7 exercises, 24.4 min, 2093 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | - | - |
| Dumbbell Hip Thrust | 3 | fits a priority-1 goal; uses equipment the member prefers | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers | - |
| Glute Bridge | 3 | fits a priority-1 goal | same pattern trained in the last two days |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers | - |
| Alternating Low Plank To Low Side Plank | 3 | - | - |
| Ground Upper Trap Stretch | 1 | - | - |

**Request read:** explosive plyometric jump training -> plyometric, jump (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Nothing matching plyometric jump passed the safety filter, so the main block uses the closest safe exercises.
- Journey-stage rule (programming.yaml, not yet signed) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the safe exercises available can't fill 30 minutes at 2 sets.
- Planned 24 of 30 minutes: not enough safe exercises to fill the time.

## no-match-injury

> Upper body today, her thingy is acting up again.

Blocked: the injury mention couldn't be resolved, so the coach was asked.

