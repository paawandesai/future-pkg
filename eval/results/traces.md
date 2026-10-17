# Plans and their traces

From the eval run of 2026-10-17 21:12 UTC (`latest.json`). Member: the fictional Jordan unless the case names another.

## brief-exclude-deadlifts

> Exclude deadlifts

17 exercises, 39.7 min, 2811 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| World's Greatest Stretch | 1 | uses only equipment the member has (Yoga Mat); loads ankle, hip, knee, thoracic spine; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Walking Toe Touches | 1 | needs no equipment; loads ankle, hip, knee, lumbar spine, shoulder; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| High Plank Bird Dog | 1 | uses only equipment the member has (Yoga Mat); loads knee, shoulder, wrist; no restriction applies; quadruped is a warm-up pattern in programming.yaml | - |
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Barbell Racked Forward Lunge | 2 | uses equipment the member prefers; uses only equipment the member has (Barbell, Plate, Rack); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder; no restriction applies; picked for the main block by the selection step | - |
| One-Kettlebell Hamstring Walkout | 2 | uses equipment the member prefers; uses only equipment the member has (Kettlebell, Yoga Mat); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Dumbbell Goblet Split Squat | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Alternating Dumbbell Racked Crossback Lunge | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Glute Bridge | 2 | uses only equipment the member has (Yoga Mat); loads hip; no restriction applies; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist; no restriction applies; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Jump Rope - Single-Leg | 2 | uses only equipment the member has (Jump Rope); loads ankle, knee; no restriction applies; picked for the main block by the selection step | - |
| Static Jump | 2 | needs no equipment; loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Bodyweight Pike | 2 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist; no restriction applies; added to the main block to fill the time window | - |
| Cow Pose | 1 | uses only equipment the member has (Yoga Mat); loads ankle, hip, knee, lumbar spine; no restriction applies; mobility - static, yoga, regen are cool-down patterns in programming.yaml | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine; no restriction applies; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** deadlifts -> Deadlift (accepted, exact)

**Restrictions:** none

**Filtered out before drafting:**

- Excluded by request (Deadlift): 2 exercises
- Needs equipment the member does not have: 35 exercises

**Notes:**
- Dropped 1 id(s) the model returned that were not on the filtered list.
- Lighter main block (2 sets each): weekly completion fell from 100% to 25% over the last 4 weeks. Journey-stage rule in programming.yaml.

## brief-left-knee

> Her left knee is bothering her

9 exercises, 33.0 min, 2281 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Romanian Deadlift | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Kettlebell Romanian Deadlift | 3 | uses equipment the member prefers; uses only equipment the member has (Kettlebell); loads hip, lumbar spine, none of them restricted; added to the main block to fill the time window | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** knee -> Knee (left) (accepted, exact)

**Restrictions:** region:knee (left) from request

**Filtered out before drafting:**

- Loads the left knee (request): 26 exercises
- Needs equipment the member does not have: 35 exercises

**Notes:**
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 25% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 40 minutes at 2 sets.
- Planned 33 of 40 minutes: not enough exercises passed the filter to fill the time.

## brief-no-barbell

> She has no barbell, only dumbbells and a kettlebell

10 exercises, 38.4 min, 2299 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Walking Toe Touches | 1 | needs no equipment; loads ankle, hip, knee, lumbar spine, shoulder; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Alternating Dumbbell Racked Crossback Lunge | 3 | uses equipment the member prefers; stands in for Barbell Racked Forward Lunge, which needs equipment the member lacks; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Dumbbell Romanian Deadlift | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads hip, lumbar spine; no restriction applies; picked for the main block by the selection step | - |
| Dumbbell Goblet Split Squat | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Kettlebell Romanian Deadlift | 3 | uses equipment the member prefers; uses only equipment the member has (Kettlebell); loads hip, lumbar spine; no restriction applies; picked for the main block by the selection step | - |
| Jumping Jack | 3 | stands in for Jump Rope - Single-Leg, which needs equipment the member lacks; needs no equipment; loads ankle, hip, knee, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Static Jump | 3 | stands in for Jump Rope - Single-Leg, which needs equipment the member lacks; needs no equipment; loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Vertical Jump to Broad Jump | 3 | needs no equipment; loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |

**Request read:** barbell -> Barbell (accepted, exact)

**Restrictions:** none

**Filtered out before drafting:**

- Needs equipment the member does not have: 46 exercises

**Equivalent alternatives:** Alternating Dumbbell Racked Crossback Lunge instead of Barbell Racked Forward Lunge; Jumping Jack instead of Jump Rope - Single-Leg; Static Jump instead of Jump Rope - Single-Leg

**Notes:**
- Only the equipment named in the request was used; left out: Jump Rope, Plate, Rack, Yoga Mat.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 25% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 40 minutes at 2 sets.

## brief-knee-example

> lower-body exercises that avoid aggravating a knee injury

9 exercises, 33.0 min, 1976 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Romanian Deadlift | 3 | matches the requested focus; uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | matches the requested focus; stands in for Dumbbell Hip Thrust, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Kettlebell Romanian Deadlift | 3 | matches the requested focus; uses equipment the member prefers; uses only equipment the member has (Kettlebell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** knee -> Knee (accepted, exact); lower-body exercises -> lower body (accepted, exact)

**Restrictions:** region:knee from request

**Filtered out before drafting:**

- Loads the knee (request): 26 exercises
- Needs equipment the member does not have: 35 exercises

**Equivalent alternatives:** Glute Bridge instead of Dumbbell Hip Thrust

**Notes:**
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 25% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 40 minutes at 2 sets.
- Only 3 of 7 main-block exercises match lower body: 3 exercise(s) matching it passed the filter. The rest are the closest exercises that passed it, used to fill the time.
- Planned 33 of 40 minutes: not enough exercises passed the filter to fill the time.

## brief-pecs-example

> full-body exercise with isolation around my pecs

11 exercises, 43.7 min, 2295 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Neutral-Grip Bench Press | 3 | matches the requested focus; uses equipment the member prefers; stands in for Alternating Dumbbell Decline Bench Press, which needs equipment the member lacks; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Hip Thrust | 3 | fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Push-Up to Knee-Drive | 3 | matches the requested focus; uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 3 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** full-body exercise -> full body (accepted, exact); pecs isolation -> chest (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Equivalent alternatives:** Dumbbell Neutral-Grip Bench Press instead of Alternating Dumbbell Decline Bench Press

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 50 minutes at 2 sets.
- Only 2 of 9 main-block exercises match full body, chest: 2 exercise(s) matching it passed the filter. The rest are the closest exercises that passed it, used to fill the time.
- Planned 44 of 50 minutes: not enough exercises passed the filter to fill the time.

## deadlift

> Full body 40 min, no deadlifts.

10 exercises, 39.4 min, 2853 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 3 | fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
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

## left-knee

> 45 minutes, lower body. Her left knee is still a bit sore.

11 exercises, 43.7 min, 1739 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 3 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | matches the requested focus; fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 3 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
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
- Only 2 of 9 main-block exercises match lower body: 2 exercise(s) matching it passed the filter. The rest are the closest exercises that passed it, used to fill the time.

## left-knee-cleared

> 45 minutes, lower body. Her left knee is still a bit sore.

18 exercises, 42.6 min, 2350 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Walking Toe Touches | 1 | needs no equipment; loads a restricted region only within the coach's low-impact clearance; loads ankle, hip, lumbar spine, shoulder, none of them restricted; mobility - dynamic is a warm-up pattern in programming.yaml | Loads the left knee (no loaded knee bend); coach cleared low-impact loading |
| High Plank Bird Dog | 1 | uses only equipment the member has (Yoga Mat); loads a restricted region only within the coach's low-impact clearance; loads shoulder, wrist, none of them restricted; quadruped is a warm-up pattern in programming.yaml | Loads the left knee (no loaded knee bend); coach cleared low-impact loading |
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 2 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers; stands in for Med Ball Hamstring Walkout, which needs equipment the member lacks; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| High-Box Goblet Squat (partial range) | 2 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads a restricted region only within the coach's low-impact clearance; loads ankle, hip, none of them restricted; picked for the main block by the selection step | same pattern trained in the last two days; Loads the left knee (shallow knee bend, up to about 45°); coach cleared low-impact loading |
| One-Kettlebell Hamstring Walkout | 2 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers; stands in for Med Ball Hamstring Walkout, which needs equipment the member lacks; uses only equipment the member has (Kettlebell, Yoga Mat); loads a restricted region only within the coach's low-impact clearance; loads ankle, hip, none of them restricted; picked for the main block by the selection step | same pattern trained in the last two days; Loads the left knee (shallow knee bend, up to about 45°); coach cleared low-impact loading |
| Low Copenhagen Plank | 2 | matches the requested focus; fits a priority-1 goal; uses only equipment the member has (Flat Bench, Yoga Mat); loads a restricted region only within the coach's low-impact clearance; loads ankle, hip, shoulder, none of them restricted; picked for the main block by the selection step | Loads the left knee (no loaded knee bend); coach cleared low-impact loading |
| Banded Lateral Walk | 2 | matches the requested focus; fits a priority-1 goal; uses only equipment the member has (Resistance Band - Loop); loads a restricted region only within the coach's low-impact clearance; loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days; Loads the left knee (shallow knee bend, up to about 45°); coach cleared low-impact loading |
| Glute Bridge | 2 | matches the requested focus; fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 2 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Neutral-Grip Bench Press | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; added to the main block to fill the time window | - |
| Push-Up to Knee-Drive | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; added to the main block to fill the time window | - |
| Resistance Band Reverse Curl | 2 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; added to the main block to fill the time window | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |
| Cow Pose | 1 | uses only equipment the member has (Yoga Mat); loads a restricted region only within the coach's low-impact clearance; loads ankle, hip, lumbar spine, none of them restricted; mobility - static, yoga, regen are cool-down patterns in programming.yaml | Loads the left knee (no loaded knee bend); coach cleared low-impact loading; Kneeling puts direct pressure on the front of the knee; ask the member how it feels. |

**Request read:** knee -> Knee (left) (accepted, exact); lower body -> lower body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 15 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Equivalent alternatives:** Dumbbell Hip Thrust instead of Med Ball Hamstring Walkout; One-Kettlebell Hamstring Walkout instead of Med Ball Hamstring Walkout

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Lighter main block (2 sets each): weekly completion fell from 100% to 50% over the last 4 weeks. Journey-stage rule in programming.yaml.
- Only 6 of 13 main-block exercises match lower body: 6 exercise(s) matching it passed the filter. The rest are the closest exercises that passed it, used to fill the time.

## no-barbell

> 30 min upper body. She has no barbell and no bench this week.

8 exercises, 28.7 min, 4360 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Alternating Dumbbell Overhead Press | 3 | matches the requested focus; uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | matches the requested focus; uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 3 | matches the requested focus; stands in for Single-Arm Dumbbell Preacher Curl, which needs equipment the member lacks; uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | fits a priority-1 goal; stands in for Dumbbell Hip Thrust, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** barbell -> Barbell (accepted, exact); bench -> Flat Bench (accepted, exact); upper body -> upper body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 34 exercises

**Equivalent alternatives:** Glute Bridge instead of Dumbbell Hip Thrust; Resistance Band Reverse Curl instead of Single-Arm Dumbbell Preacher Curl

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 30 minutes at 2 sets.

## no-dumbbells

> Upper body, 30 minutes, she left her dumbbells at the office.

7 exercises, 24.4 min, 2087 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Push-Up to Knee-Drive | 3 | matches the requested focus; uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
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

**Equivalent alternatives:** Resistance Band Reverse Curl instead of Single-Arm Dumbbell Preacher Curl; Glute Bridge instead of Dumbbell Hip Thrust

**Notes:**
- Left out 1 exercise(s) the member says they dislike: Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 30 minutes at 2 sets.
- Only 2 of 5 main-block exercises match upper body: 2 exercise(s) matching it passed the filter. The rest are the closest exercises that passed it, used to fill the time.
- Planned 24 of 30 minutes: not enough exercises passed the filter to fill the time.

## no-match-focus

> Explosive plyometric jump training, 30 minutes.

11 exercises, 28.0 min, 1899 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 2 | fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 2 | fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Neutral-Grip Bench Press | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 2 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 2 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; added to the main block to fill the time window | - |
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
- Lighter main block (2 sets each): weekly completion fell from 100% to 50% over the last 4 weeks. Journey-stage rule in programming.yaml.

## no-match-injury

> Upper body today, her thingy is acting up again.

Blocked: the injury mention couldn't be resolved, so the coach was asked.

## no-match-injury-confirmed

> Upper body today, her thingy is acting up again.

5 exercises, 15.7 min, 1967 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Hip Thrust | 3 | fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Glute Bridge | 3 | fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; added to the main block to fill the time window | same pattern trained in the last two days |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** her thingy is acting up again -> nothing (no_match, none); upper body -> upper body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left; region:elbow from coach-confirmed

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Loads the elbow (coach confirmed): 20 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Nothing matching upper body passed the safety filter, so the main block uses the closest exercises that passed the filter.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 50 minutes at 2 sets.
- Planned 16 of 50 minutes: not enough exercises passed the filter to fill the time.

## knee-surgery

> Lower body, 45 minutes. She had knee surgery three weeks ago.

9 exercises, 33.0 min, 2211 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Romanian Deadlift | 3 | matches the requested focus; uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | matches the requested focus; stands in for Dumbbell Hip Thrust, which needs equipment the member lacks; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | - |
| Kettlebell Romanian Deadlift | 3 | matches the requested focus; uses equipment the member prefers; uses only equipment the member has (Kettlebell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** knee -> Knee (accepted, exact); Lower body -> lower body (accepted, exact)

**Restrictions:** region:knee from request

**Filtered out before drafting:**

- Loads the knee (request): 26 exercises
- Needs equipment the member does not have: 35 exercises

**Equivalent alternatives:** Glute Bridge instead of Dumbbell Hip Thrust

**Notes:**
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 25% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 45 minutes at 2 sets.
- Only 3 of 7 main-block exercises match lower body: 3 exercise(s) matching it passed the filter. The rest are the closest exercises that passed it, used to fill the time.
- Planned 33 of 45 minutes: not enough exercises passed the filter to fill the time.

## tennis-elbow

> Upper body. She has tennis elbow on the right.

17 exercises, 39.7 min, 1789 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| World's Greatest Stretch | 1 | uses only equipment the member has (Yoga Mat); loads ankle, hip, knee, thoracic spine, none of them restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| High Plank Bird Dog | 1 | uses only equipment the member has (Yoga Mat); loads knee, shoulder, wrist, none of them restricted; quadruped is a warm-up pattern in programming.yaml | - |
| Walking Toe Touches | 1 | needs no equipment; loads ankle, hip, knee, lumbar spine, shoulder, none of them restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Barbell Racked Forward Lunge | 2 | uses equipment the member prefers; uses only equipment the member has (Barbell, Plate, Rack); loads ankle, hip, knee, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Romanian Deadlift | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Goblet Split Squat | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee, none of them restricted; picked for the main block by the selection step | - |
| One-Kettlebell Hamstring Walkout | 2 | uses equipment the member prefers; uses only equipment the member has (Kettlebell, Yoga Mat); loads ankle, hip, knee, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Racked Crossback Lunge | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee, none of them restricted; picked for the main block by the selection step | - |
| Kettlebell Romanian Deadlift | 2 | uses equipment the member prefers; uses only equipment the member has (Kettlebell); loads hip, lumbar spine, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 2 | uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 2 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Jumping Jack | 2 | needs no equipment; loads ankle, hip, knee, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Jump Rope - Single-Leg | 2 | uses only equipment the member has (Jump Rope); loads ankle, knee, none of them restricted; added to the main block to fill the time window | - |
| Static Jump | 2 | needs no equipment; loads ankle, hip, knee, none of them restricted; added to the main block to fill the time window | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |
| Cow Pose | 1 | uses only equipment the member has (Yoga Mat); loads ankle, hip, knee, lumbar spine, none of them restricted; mobility - static, yoga, regen are cool-down patterns in programming.yaml | - |

**Request read:** elbow -> Elbow (accepted, exact); tennis elbow on the right -> Elbow (right) (accepted, contained); Upper body -> upper body (accepted, exact)

**Restrictions:** region:elbow from request

**Filtered out before drafting:**

- Loads the elbow (request): 20 exercises
- Needs equipment the member does not have: 35 exercises

**Notes:**
- Nothing matching upper body passed the safety filter, so the main block uses the closest exercises that passed the filter.
- Dropped 1 id(s) the model returned that were not on the filtered list.
- Lighter main block (2 sets each): weekly completion fell from 100% to 25% over the last 4 weeks. Journey-stage rule in programming.yaml.

## pregnant-clearance-note

> Full body, 40 minutes. She's 20 weeks pregnant.

17 exercises, 38.4 min, 2062 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| World's Greatest Stretch | 1 | uses only equipment the member has (Yoga Mat); loads ankle, hip, knee, thoracic spine; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Walking Toe Touches | 1 | needs no equipment; loads ankle, hip, knee, lumbar spine, shoulder; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| High Plank Bird Dog | 1 | uses only equipment the member has (Yoga Mat); loads knee, shoulder, wrist; no restriction applies; quadruped is a warm-up pattern in programming.yaml | - |
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine; no restriction applies; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Barbell Racked Forward Lunge | 2 | uses equipment the member prefers; uses only equipment the member has (Barbell, Plate, Rack); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Dumbbell Romanian Deadlift | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads hip, lumbar spine; no restriction applies; picked for the main block by the selection step | - |
| Dumbbell Goblet Split Squat | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Alternating Dumbbell Racked Crossback Lunge | 2 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Kettlebell Romanian Deadlift | 2 | uses equipment the member prefers; uses only equipment the member has (Kettlebell); loads hip, lumbar spine; no restriction applies; picked for the main block by the selection step | - |
| One-Kettlebell Hamstring Walkout | 2 | uses equipment the member prefers; uses only equipment the member has (Kettlebell, Yoga Mat); loads ankle, hip, knee; no restriction applies; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist; no restriction applies; picked for the main block by the selection step | - |
| Alternating Low Plank To Low Side Plank | 2 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder; no restriction applies; picked for the main block by the selection step | - |
| Bodyweight Pike | 2 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist; no restriction applies; added to the main block to fill the time window | - |
| Glute Bridge | 2 | uses only equipment the member has (Yoga Mat); loads hip; no restriction applies; added to the main block to fill the time window | - |
| Cow Pose | 1 | uses only equipment the member has (Yoga Mat); loads ankle, hip, knee, lumbar spine; no restriction applies; mobility - static, yoga, regen are cool-down patterns in programming.yaml | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine; no restriction applies; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** full body -> full body (accepted, exact)

**Restrictions:** none

**Filtered out before drafting:**

- Needs equipment the member does not have: 35 exercises

**Notes:**
- Check clearance: the request mentions pregnancy ("pregnant"). The filter doesn't adjust exercises for this, so check that the member is cleared for exercise before using this plan.
- Dropped 1 id(s) the model returned that were not on the filtered list.
- Lighter main block (2 sets each): weekly completion fell from 100% to 25% over the last 4 weeks. Journey-stage rule in programming.yaml.

## left-knee-cleared-but-painful

> 45 minutes, lower body. Her left knee is really painful today.

11 exercises, 43.7 min, 2262 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 3 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Glute Bridge | 3 | matches the requested focus; fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 3 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** knee -> Knee (left) (accepted, exact); lower body -> lower body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left; region:knee (left) from request

**Filtered out before drafting:**

- Loads the left knee (request): 26 exercises
- Loads the left knee (member record): 15 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- The request mentions pain or injury at the left knee, so the coach's low-impact clearance for it was not applied to this draft. Every exercise that loads it is left out.
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 45 minutes at 2 sets.
- Only 2 of 9 main-block exercises match lower body: 2 exercise(s) matching it passed the filter. The rest are the closest exercises that passed it, used to fill the time.

