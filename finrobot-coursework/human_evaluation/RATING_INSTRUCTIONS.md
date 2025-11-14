# Human Evaluation Instructions

**Study**: Comparing AI Systems for Financial Analysis
**Time Required**: ~45-60 minutes
**Compensation**: [Your offer - e.g., $25 Amazon gift card or authorship credit]

---

## Your Task

You will rate **50 financial analysis outputs** from two different AI systems (SYSTEM_A and SYSTEM_B). The systems are anonymized - you should not know which is which.

For each output, rate the **overall quality** on a 1-5 scale.

---

## Rating Scale

**5 - Excellent**: Highly insightful, well-structured, actionable analysis with clear reasoning

**4 - Good**: Solid analysis with useful insights, minor gaps or verbosity

**3 - Acceptable**: Basic analysis present, but lacks depth or has some issues

**2 - Poor**: Superficial or disorganized, minimal useful insight

**1 - Very Poor**: Confusing, incorrect, or mostly data dumps without analysis

---

## What to Look For

### ✅ GOOD Qualities (Rate Higher):
- **Clear structure**: Organized into positives, concerns, prediction
- **Analytical insights**: Explains WHY things matter, not just WHAT they are
- **Specific evidence**: Cites numbers, percentages, trends
- **Actionable conclusions**: Clear directional call (buy/sell/hold) with justification
- **Conciseness**: Gets to the point without excessive repetition

### ❌ BAD Qualities (Rate Lower):
- **Data dumps**: Lists facts without interpretation
- **Vague statements**: "Stock might go up or down"
- **No reasoning**: States conclusion without supporting logic
- **Repetitive**: Says same thing multiple times
- **Disorganized**: Scattered thoughts, hard to follow

---

## Example Ratings

### Example 1: Rating = 5 (Excellent)
```
**Positive Developments:**
1. Revenue growth of 15.3% YoY driven by cloud services expansion
2. Operating margins improved from 22% to 27% due to cost optimization
3. Recent product launch expected to drive 8% revenue increase in Q4

**Concerns:**
1. Rising interest rates pressuring P/E multiples (industry average declined 12%)
2. Competitive pressure from 3 new entrants in core market

**Prediction:**
Forecast 6% upside over next week based on strong earnings momentum
outweighing macro headwinds. Target price $165-170.
```
**Why 5**: Clear structure, specific numbers, causal reasoning, actionable call

---

### Example 2: Rating = 2 (Poor)
```
AAPL current price: $150.234567 (2024-01-15)
Price on 2024-01-14: $150.123456
Price on 2024-01-13: $151.234567
Price on 2024-01-12: $150.987654

Recent news:
- "Apple announces Q4 results" (Jan 10)
- "iPhone sales strong" (Jan 8)

Financial metrics:
- P/E Ratio: 28.56
- EPS: $6.12
- Revenue: $394.3B

Market conditions may affect stock price.
```
**Why 2**: Just data dumps, no analysis, vague conclusion, excessive precision

---

## How to Rate

### Step 1: Read the Output
Read the full financial analysis for the given ticker.

### Step 2: Ask Yourself
- "Would this help me make an investment decision?"
- "Does it explain WHY, not just WHAT?"
- "Is it well-organized and actionable?"

### Step 3: Assign Rating (1-5)
Use the scale above. When in doubt, go with your gut - you're the expert.

### Step 4: Optional Comments
If you want, add brief notes (1-2 sentences) explaining your rating. This helps us improve.

---

## Data Collection

### Option A: Google Form
[Link to form] - We'll set this up for you

### Option B: CSV File
Open `rating_sheet.csv` and fill in the "Quality_Score_(1-5)" column for each sample.

### Option C: JSON File
Edit `your_ratings.json` with your scores.

---

## Important Notes

1. **Blind Rating**: You should NOT know which system is which (SYSTEM_A vs SYSTEM_B)
2. **Expertise**: You don't need to be a finance expert - common sense judgments are fine
3. **Consistency**: Try to use the same standards across all 50 samples
4. **Honesty**: Rate based on quality, not which system you think produced it
5. **Time**: Don't overthink - spend ~1 minute per sample (first impressions work)

---

## After You're Done

1. Save your ratings (CSV or JSON)
2. Send to: [your email]
3. We'll analyze inter-rater agreement (Cohen's kappa)
4. Results will be published in research paper
5. You'll receive acknowledgment (and compensation if applicable)

---

## Questions?

Contact: [Your name/email]

**Thank you for helping advance financial AI research!** 🎓
