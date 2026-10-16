# Plans and their traces

From the eval run of 2026-10-16 21:40 UTC (`latest.json`). Member: the fictional Jordan unless the case names another (the `brief-*` adjustment rows run on Elena and Sam).

## brief-exclude-deadlifts

> Exclude deadlifts

16 exercises, 35.7 min, 3102 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| World's Greatest Stretch | 1 | uses only equipment the member has (Yoga Mat); loads ankle, hip, knee, thoracic spine; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Walking Toe Touches | 1 | needs no equipment; loads ankle, hip, knee, lumbar spine, shoulder; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| High Plank Bird Dog | 1 | uses only equipment the member has (Yoga Mat); loads knee, shoulder, wrist; no restriction applies; quadruped is a warm-up pattern in programming.yaml | - |
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Goblet Split Squat | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Alternating Dumbbell Racked Crossback Lunge | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| One-Kettlebell Hamstring Walkout | 2 | uses equipment the member prefers; uses only equipment the member has (Kettlebell, Yoga Mat); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist; no restriction applies; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Jump Rope - Single-Leg | 2 | uses only equipment the member has (Jump Rope); loads ankle, knee; no restriction applies; picked for the main block by the selection step | - |
| Glute Bridge | 2 | uses only equipment the member has (Yoga Mat); loads hip; no restriction applies; picked for the main block by the selection step | - |
| Jumping Jack | 2 | needs no equipment; loads ankle, hip, knee, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Static Jump | 2 | needs no equipment; loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Cow Pose | 1 | uses only equipment the member has (Yoga Mat); loads ankle, hip, knee, lumbar spine; no restriction applies; mobility - static, yoga, regen are cool-down patterns in programming.yaml | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine; no restriction applies; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** deadlifts -> Deadlift (accepted, exact)

**Restrictions:** none

**Filtered out before drafting:**

- Excluded by request (Deadlift): 2 exercises
- Needs equipment the member does not have: 36 exercises

**Notes:**
- Dropped 1 id(s) the model returned that were not on the filtered list.
- Lighter main block (2 sets each): weekly completion fell from 100% to 25% over the last 4 weeks. Journey-stage rule in programming.yaml.
- Planned 36 of 40 minutes: not enough exercises passed the filter to fill the time.

## brief-left-knee

> Her left knee is bothering her

9 exercises, 31.4 min, 2307 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Romanian Deadlift | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Kettlebell Romanian Deadlift | 2 | uses equipment the member prefers; uses only equipment the member has (Kettlebell); loads hip, lumbar spine, none of them restricted; added to the main block to fill the time window | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** knee -> Knee (left) (accepted, exact)

**Restrictions:** region:knee (left) from request

**Filtered out before drafting:**

- Loads the left knee (request): 26 exercises
- Needs equipment the member does not have: 36 exercises

**Notes:**
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 25% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 40 minutes at 2 sets.
- Planned 31 of 40 minutes: not enough exercises passed the filter to fill the time.

## brief-no-barbell

> She has no barbell, only dumbbells and a kettlebell

8 exercises, 29.7 min, 3013 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Walking Toe Touches | 1 | needs no equipment; loads ankle, hip, knee, lumbar spine, shoulder; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Alternating Dumbbell Overhead Press | 3 | fits a priority-1 goal; uses only equipment the member has (Dumbbell); loads elbow, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Alternating Dumbbell Racked Crossback Lunge | 3 | stands in for Barbell Racked Forward Lunge, which needs equipment the member lacks; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Dumbbell Romanian Deadlift | 3 | uses only equipment the member has (Dumbbell); loads hip, lumbar spine; no restriction applies; picked for the main block by the selection step | - |
| Vertical Jump to Broad Jump | 3 | stands in for High-Box Goblet Squat (partial range), which needs equipment the member lacks; needs no equipment; loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Dumbbell Goblet Split Squat | 3 | uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Jumping Jack | 3 | needs no equipment; loads ankle, hip, knee, shoulder; no restriction applies; picked for the main block by the selection step | - |

**Request read:** barbell -> Barbell (accepted, exact)

**Restrictions:** none

**Filtered out before drafting:**

- Needs equipment the member does not have: 47 exercises

**Equivalent alternatives:** Alternating Dumbbell Racked Crossback Lunge instead of Barbell Racked Forward Lunge; Vertical Jump to Broad Jump instead of High-Box Goblet Squat (partial range)

**Notes:**
- Only the equipment named in the request was used; left out: Flat Bench, Plate, Rack.
- Planned 30 of 40 minutes: not enough exercises passed the filter to fill the time.

## brief-knee-example

> lower-body exercises that avoid aggravating a knee injury

9 exercises, 31.4 min, 3345 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Romanian Deadlift | 3 | matches the requested focus; uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | matches the requested focus; stands in for Dumbbell Hip Thrust, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | - |
| Kettlebell Romanian Deadlift | 3 | matches the requested focus; uses equipment the member prefers; uses only equipment the member has (Kettlebell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** knee -> Knee (accepted, exact); lower-body exercises -> lower body (accepted, exact)

**Restrictions:** region:knee from request

**Filtered out before drafting:**

- Loads the knee (request): 26 exercises
- Needs equipment the member does not have: 36 exercises

**Equivalent alternatives:** Glute Bridge instead of Dumbbell Hip Thrust

**Notes:**
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 25% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 40 minutes at 2 sets.
- Planned 31 of 40 minutes: not enough exercises passed the filter to fill the time.

## brief-pecs-example

> full-body exercise with isolation around my pecs

10 exercises, 39.4 min, 1802 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Neutral-Grip Bench Press | 3 | matches the requested focus; uses equipment the member prefers; stands in for Alternating Dumbbell Decline Bench Press, which needs equipment the member lacks; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Hip Thrust | 3 | fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Push-Up to Knee-Drive | 3 | matches the requested focus; stands in for Alternating Dumbbell Decline Bench Press, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 3 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** full-body -> full body (accepted, exact); pecs -> chest (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Equivalent alternatives:** Dumbbell Neutral-Grip Bench Press instead of Alternating Dumbbell Decline Bench Press; Push-Up to Knee-Drive instead of Alternating Dumbbell Decline Bench Press

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 50 minutes at 2 sets.
- Planned 39 of 50 minutes: not enough exercises passed the filter to fill the time.

## deadlift

> Full body 40 min, no deadlifts.

8 exercises, 30.7 min, 3102 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 3 | fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** deadlifts -> Deadlift (accepted, exact); full body -> full body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Excluded by request (Deadlift): 2 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 40 minutes at 2 sets.
- Planned 31 of 40 minutes: not enough exercises passed the filter to fill the time.

## left-knee

> 45 minutes, lower body. Her left knee is still a bit sore.

10 exercises, 35.7 min, 1749 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 3 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | matches the requested focus; fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 2 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** knee -> Knee (left) (accepted, exact); lower body -> lower body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 45 minutes at 2 sets.
- Planned 36 of 45 minutes: not enough exercises passed the filter to fill the time.

## no-barbell

> 30 min upper body. She has no barbell and no bench this week.

7 exercises, 24.4 min, 1581 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | stands in for Bench-Supported Incline YTI, which needs equipment the member lacks; needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Alternating Dumbbell Overhead Press | 3 | matches the requested focus; uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | matches the requested focus; stands in for Barbell Decline Bench Press, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 3 | matches the requested focus; stands in for Single-Arm Dumbbell Preacher Curl, which needs equipment the member lacks; uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | fits a priority-1 goal; stands in for Dumbbell Hip Thrust, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** barbell -> Barbell (accepted, exact); bench -> Flat Bench (accepted, exact); upper body -> upper body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 34 exercises

**Equivalent alternatives:** Push-Up to Knee-Drive instead of Barbell Decline Bench Press; Glute Bridge instead of Dumbbell Hip Thrust; Standing Neck Circles instead of Bench-Supported Incline YTI; Resistance Band Reverse Curl instead of Single-Arm Dumbbell Preacher Curl

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 30 minutes at 2 sets.
- Planned 24 of 30 minutes: not enough exercises passed the filter to fill the time.

## no-dumbbells

> Upper body, 30 minutes, she left her dumbbells at the office.

7 exercises, 24.4 min, 2773 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | stands in for Bench-Supported Incline YTI, which needs equipment the member lacks; needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Push-Up to Knee-Drive | 3 | matches the requested focus; stands in for Alternating Dumbbell Decline Bench Press, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 3 | matches the requested focus; stands in for Single-Arm Dumbbell Preacher Curl, which needs equipment the member lacks; uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | fits a priority-1 goal; stands in for Dumbbell Hip Thrust, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** dumbbells -> Dumbbell (accepted, exact); upper body -> upper body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 37 exercises

**Equivalent alternatives:** Push-Up to Knee-Drive instead of Alternating Dumbbell Decline Bench Press; Resistance Band Reverse Curl instead of Single-Arm Dumbbell Preacher Curl; Glute Bridge instead of Dumbbell Hip Thrust; Standing Neck Circles instead of Bench-Supported Incline YTI

**Notes:**
- Left out 1 exercise(s) the member says they dislike: Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 30 minutes at 2 sets.
- Planned 24 of 30 minutes: not enough exercises passed the filter to fill the time.

## no-match-focus

> Explosive plyometric jump training, 30 minutes.

7 exercises, 24.7 min, 2341 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 3 | fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Neutral-Grip Bench Press | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** explosive plyometric jump training -> plyometric, jump (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Nothing matching plyometric jump passed the safety filter, so the main block uses the closest exercises that passed the filter.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 30 minutes at 2 sets.
- Planned 25 of 30 minutes: not enough exercises passed the filter to fill the time.

## no-match-injury

> Upper body today, her thingy is acting up again.

Blocked: the injury mention couldn't be resolved, so the coach was asked.

