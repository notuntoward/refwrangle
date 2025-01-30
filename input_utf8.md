### Harvard Data Science Review â¢ Issue 6.4, Fall 2024

# Forecasting Turnout

### Stephen Ansolabehere[1] Jacob Brown[2] Kabir Khanna[3] Connor Phillips[4]
 Charles Stewart III[5]

**1Department of Government, Harvard University, Cambridge, Massachusetts, United States of**
**America,**

**2Department of Political Science, Boston University, Boston, Massachusetts, United States of**
**America,**

**3CBS Decision Desk, New York, New York, United States of America,**

**4Department of Political Science, Vanderbilt University, Nashville, Tennessee, United States of**
**America,**

**5Department of Political Science, Massachusetts Institute of Technology, Cambridge,**
**Massachusetts, United States of America**

##### The MIT Press

 Published on: Oct 17, 2024

 DOI: https://doi.org/10.1162/99608f92.62881547

 License: Creative Commons Attribution 4.0 International License (CC-BY 4.0)


-----

ABSTRACT

We evaluate the predictive power of the leading explanatory models of turnout in the academic literature. We

compare the power of using registration, lagged vote, demographics, electoral competition, and early vote data

to predict turnout. We specify models to capture each of these approaches to understanding turnout, fit those

models to the relevant data from prior elections, and use the estimated parameters from prior years and the

relevant observable data from the day of the election in the current year to predict that yearâs election. The

simplest and most naive model, the Registration Model, outperformed other models in predicting 2016 turnout

using 2012 election data and 2020 turnout using 2016 election data. These findings are consistent with classic

understandings of which factors most drive turnout, and demonstrate that in modern elections the propensity of

registered voters to turn out in presidential elections is fairly stable. Saturated models that combine many of

these predictors are common in the academic literature that attempts to explain levels of turnout. We find that

such saturated models overfit the data and lead to less accurate predictions than parsimonious models.

**Keywords: Elections, turnout, prediction, registration, modeling**

## Media Summary

We evaluate leading predictive models of turnout across counties and districts: comparing the predictive power

of registration, lagged vote, demographics, electoral competition, and early vote data. We fit these models

separately by each state to data from prior elections to predict turnout based on data as of the day of the

election in a given election year. We find that the number of registrants in a county or district at the time of the

election is the best predictor of turnout in that election, and that combining this simple model with

demographic, electoral competition, or other information provides limited utility for explaining turnout. These

findings imply that turnout rates among registered voters across recent presidential elections are stable, so the

relationship between registration and turnout from previous elections is a consistent predictor of turnout in

coming elections.

## 1. Introduction

Prediction is a basic standard against which scientific progress can be gauged (Forster, 2002). Much modern

political science concerns itself with measurement, explanation, and causality, but pays less attention to

prediction (Clark & Golder, 2015; Grimmer, 2015; Monroe et al., 2015). Ultimately, though, the value of our

science rests with our ability to predict. For example, how well we can predict voting behavior in future

elections is a function of scientific progress in understanding how elections work (Dowding & Miller, 2019).

Furthermore, election prediction influences media coverage of elections (Dowding, 2021; Westwood et al.,

2020), campaign strategy (Hersh, 2015), and election administration (Burden & Stewart, 2014; Burden et al.,


-----

2014). This article considers one such political science problemâpredicting turnout. Is our understanding of

behavior and the processes that produce it good enough to predict future behavior using a model that captures

our understanding? Developing a forecasting model of turnout offers insight into how we explain participation

but is also of tremendous practical value.

Our own experience with the problem of forecasting turnout comes every election night. We are members of a

team of analysts at CBS News headquarters in New York. We examine the real-time, but incomplete, vote

tallies from the states and project who won the U.S. presidency and seats in the U.S. House and Senate based

on those incomplete data. We work much like similar groups at ABC, NBC, CNN, FOX News, and the

Associated Press. When we make a determination, it is based on a projection of the total votes that were cast,

who won the votes that have been counted, and what the likely outcome will be among the votes that have yet

to be counted. To correctly determine who won and who lost often requires, first, an accurate estimate of the

total votes that will be cast. In some states it will take weeks to finish counting the ballots, yet on election night

we have fairly accurate projections of turnout and of the winners.[1]

The national media are not alone in making predictions about turnout. Every election administrator in the

United States needs to gauge how many votes are likely to be cast in order to plan and manage the election.

Election lawyers and advocates for election integrity detect irregularities by comparing actual tallies to

expected vote totals (Corasaniti, 2021). Campaign organizations use turnout predictions to know where to

make a final push for voter mobilization.[2] And, academic researchers need to project a counterfactual level of

turnout in order to measure the effects of interventions, such as campaign communications or new voting

procedures (A. Fowler, 2015).[3] The problem is this: On the morning of Election Day, what is our best forecast

for what turnout will be throughout the nation, in every state, and in each congressional district (CD)? These

are the jurisdictions for which forecasts need to be made for election night projections of who won, for

monitoring election integrity, and for gauging the counterfactual level of turnout in the absence of field

experiments and other interventions.

The scholarly literature on forecasting aggregate turnout is surprisingly thin. Extensive research, relying on

self-reported vote and, increasingly, on data from voter files, examines which demographic groups voted and

which did not (Hersh, 2015; Leighley & Nagler, 2013; Rosenstone & Hansen, 1993). And, a long-lineage of

research has sought to measure the effects of changes in election laws and in the demography of the United

States on aggregate turnout (Burnham, 1974; Converse, 1972; Rusk, 1974). Much recent work tests the causal

mechanisms behind individual turnout decisions (Blais, 2006; Cantoni & Pons, 2022; Enos & Fowler, 2014; J.

H. Fowler & Dawes, 2008; Gerber et al., 2003). Almost none of this work has used these models to predict

turnout levels in subsequent elections, a task we face every election year.

This article examines five strategies and types of models for forecasting turnout. Our approach is to specify

different models, fit those models to the relevant data from prior elections, and use the estimated parameters

from prior years and the relevant observable data from the day of the election in the current year to predict that


-----

yearâs election. The models we examine are leading models of participation and turnout in the existing

academic literature that express an important line of thinking or understanding of electoral participation. They

are not exclusive of one another, and it may be possible to combine them. We treat each as a distinct approach

and examine each separately. One caution in combining these models, as we illustrate, is that one can overfit to

data from prior elections, introducing additional bias and uncertainty into forecasts.

The first model is the simplest. We call it the Registration Model. Assume that the percent of registered voters

who turn out in a jurisdiction is the same year to year; all that drives aggregate turnout is total registration. This

model has its roots in the classic Who Votes? by Wolfinger and Rosenstone (1980). They describe a two-stage

process of registration and voting, and note that registration is a significant screen in the process.

The second model considers turnout as a dynamic process, where the best predictor of future voting at the

individual level is whether an individual voted in the prior election. Models that predict turnout using lagged

vote alone have been deployed in the individual literature to capture âhabitualâ behavior (Gerber et al., 2003).

The idea behind this approach is either that lagged vote is a sufficient statistic that summarizes the

characteristics of the people in an area and their propensities to vote or that lagged vote captures a behavioral

change such that people who voted become more likely to vote and people who did not become less likely to

vote. The best predictor of whether an individual votes is whether that individual voted in the prior election. By

that reasoning, the best predictor of voting in any given area is the turnout in that areaâs last election.j

The third model is the Demographic Model, and it represents the most widely used approach for explaining

turnout at the individual level. This model posits that different demographic groups have different propensities

to vote; variation and changes in the demographic composition of the electorate are the basis for projecting

where and when turnout will be higher or lower. See, for example, Brady et al. (1995), Rosenstone & Hansen

(1993), and Leighley and Nagler (2013).

The fourth model is the Competition Model. It asserts that campaign activities or competitiveness of elections

explains where and when turnout will be higher or lower relative to a normal or average level of turnout.

Researchers have found that closeness of the election is a good shorthand for the wide range of activities and

factors that affect competition; also the absence of an election, or being a non-battleground state often proxies

for competition (Fraga & Hersh, 2018). We use closeness of the election in a state or district as the indicator of

competitiveness and campaign intensity and lagged turnout to gauge expected turnout.

The fifth model is the Early Vote Model, using early and absentee vote data. We first encountered this model

through conversations with county election officials, some of whom use the early vote to project total turnout.

The total vote can be separated into the total early and absentee vote and the total Election Day Vote. Divide

registrants into those who voted absentee (which one knows on Election Day) and those registrants who voted

on Election Day; then, use past election data to estimate the percent of registrants who voted on Election Day,

given that they did not vote absentee, in order to estimate the number of registrants who have not voted early


-----

and absentee but may vote on Election Day. This model has a particular advantage in states and counties where

absentee and early voting is universal (e.g., Oregon) or the vast majority of votes cast (e.g., Arizona).

Finally, we combine all five approaches in a single âsuper model.â In this model, one may think of lagged vote

as measuring the differential vote propensity of individuals, and thus of areas, and the other factors, such as

changes in registration, demographics, and competitiveness as accounting for important variation around that

baseline.

One model that appears in the literature that we do not present hereâthe âlikely voter modelâ of survey

researchers (Rentsch et al., 2020). The Gallup Poll popularized the likely voter model. Their approach was to

ask people how likely they are to vote, and use those people who said they are likely to vote as the predicted

turnout. These measures and estimates provided sufficiently unreliable estimates for projecting national turnout

(let alone local turnout) that Gallup no longer makes a turnout projection. There is a further limitation of the

survey data, which is that there are not sufficiently large samples at the CD, county, or even state level to

forecast turnout at those levels using survey data.

To estimate and test these models, we developed a database of registration, turnout, election results, and

demographics at the county and CD level in the United States in 2012, 2016, and 2020. The simplest and most

naive model, the Registration Model, outperformed other models in predicting 2016 turnout using 2012

election data and 2020 turnout using 2016 election data. As a check on this model, we used the Current

Population Survey to estimate turnout as a percentage of registrations, and data on total registrations nationally

from 1972 to 2020. The simple logic suggested by Rosenstone & Hansen (1993) works even there. Over time,

approximately the same proportion of registered voters turn out, but what changes is the number of registrants

in the system. Although the aim of this exercise is not to explain turnout, the implications of this analysis for

the study of participation are clear. The propensity of registered voters to turn out in presidential elections is

fairly stable. The institutions and rules that shape registration, to a first order, shape the level of turnout in the

United States.

The combined model provides a humbling lesson as well. Adding more variables to the Registration Model

actually made predictions worse!

## 2. Models and Methods

### 2.1. Models

We investigate the predictive power of five different approaches, plus a combined model.

#### Model 1. The Registration Model

We first consider the Registration Model, which predicts turnout as a function of the number of registered

voters in a county or district during an election. Let Vt be the total number of Votes cast at year and t _Rt be_


-----

the total number of persons registered to vote at year . Assume that the percent of registered voters who vote t

is constant,, from year to year, and that the only factor that varies is the number of people who are registered. v

Then,


Rt


##### Vt = vRt

is known in advance of Election Day, and the percent of registered voters who vote is observed in the prior


election as _Vtâ1_ = _v._

_Rtâ1_

To the extent that the turnout rate among registered voters does not vary across years, the number of registered

voters will be highly predictive of total turnout. We can estimate the relationship between total votes and total


registration across counties or districts through the following linear model fit to a single year of the data:t

##### Vt,g = Î±(t) + Î²(t)Rt,g + Ïµ(gt) (2.1)

(t)

where Vt is the total number of votes cast at year in geography, t _g Î±t_ is the intercept for the model in year

(t)

t R, t,g is the total number of persons registered to vote at year in geography, and t g Ïµg is the error term.

The quantity of interest is Î² [(][t][)], which represents the increase in total votes that is expected from an additional


registered voter in the electorate in year .t

We then predict turnout in the next election (election t + 1) by the following model:


##### V[^]t+1,g = Î±(t) + Î²[^][(][t][)]Rt+1,g (2.2)

#### Model 2. The Lagged Turnout (or Dynamic) Model

The Lagged Vote Model considers whether the best predictor of individual turnout is whether that individual

voted in the prior election. Likewise, the best predictor of voting in any given area is the turnout in that area j

from the last election. For this model, we estimate the following linear model across counties or districts:

##### Vt,g = Î±(t) + Î²(t)Vtâ1,g + Ïµt,g (2.3)


where Vt,g is the number of votes in geography during election, g _t Î±[(][t][)]_ is the intercept for the fitted model

from the data for election, and t _Ïµt,g_ is the error term. The quantity of interest in this case, Î² [(][t][)], represents the

correspondence between past turnout and future turnout across geographies. We estimate these parameters

from this model and then predict turnout in the following election as so:

##### V[^]t+1,g = Î±^[(][t][)] + Î²[^][(][t][)]Vt,g (2.4)

Note that the Registration and Lagged Vote Models can be combined. In the combined model, we can think of

the lagged vote as measuring the differential vote propensity, while the simple Registration Model assumes that

propensity is fixed. In the results section we present performance metrics for each model separately and then

demonstrate the performance of different combinations of our five turnout models.


-----

#### Model 3. The Demographic Model

Next we consider the predictive power of county- or district-level demographics. Let Xt be a set of


demographic characteristics. Consider turnout as a function of these demographics prior to an election, where

each demographic variable has an additive predictive effect on total votes in that election. Thus,

##### Vt = X Î²t + Ïµt

Assuming the coefficients are fairly stable, then the vote can be forecast by estimating from the prior Î² _Î²_

election and using the estimated coefficients times the current values of Xt to forecast Vt . As such, we

estimate the following model across counties or districts for a prior election to estimate the vector of t

coefficients, which consists of the coefficients for each demographic variable:Î²


##### Vg,t = Î±(t) + Î²(t)Xg,t + Ïµ(gt) (2.5)

With the estimated coefficients from this model we then predict turnout in the next election through the

following model:

##### V[^]g,t+1 = Î±^[(][t][)] + Î²[^][(][t][)]Xg,t+1 (2.6)

To operationalize this model, we include demographic characteristics at the county or district level that are

commonly found to be associated with individual or aggregate turnout. We include total population to account

for county/district size and to stabilize other predictors that are proportions. We include the percentage of the

population in a county or district that is married, as married people tend to vote at higher rates than unmarried

(Olsen, 1972). We also include college graduation rates and median household income, as income and

education are common predictors of higher turnout (Brady et al., 1995). We similarly include racial

demographics, as the American electorate tends to have significant turnout gaps by race (Fraga, 2018). Lastly,

given the strong correlation with participation, registration, and age (Ansolabehere et al., 2012), we include age

demographic information as well.

#### Model 4. The Competition Model

The fourth model we consider conceptualizes turnout as a function of the electoral competition of a given

election and/or area. By competition, we mean the extent to which an election is close, with either partyâs

candidate having a reasonable chance of electoral victory. Thus, the difference in estimated vote share from

polling or previous elections can define the electoral competition for a district (Fraga & Hersh, 2018). Previous

research has shown that turnout is often higher in more competitive elections, and campaign finance is more

focused on electorally competitive areas (Blais, 2006; Thomsen, 2023).


Let Cg,t be the competitiveness of the election in geography during election, measured by closeness in the g _t_

polls, campaign spending, or closeness of past election returns. Let Xg,t be the total population in each county

or district as of election year .t [4]


-----

##### Vg,t = Î±(t) + Î²(t)Cg,t + Xg,t + Ïµ(gt) (2.7)

We predict turnout in the next election through the following model using the coefficients from equation 7:

##### V[^]g,t+1 = Î±^[(][t][)] + Î²[^][(][t][)]Cg,t+1 + Xg,t+1 (2.8)

#### Model 5. Early Vote Model

Define Dt to be the total votes cast on Election Day and At to be the total Advanced Vote. Let Rt be the total

number of registered voters in election . We can conceptualize the total number of votes cast as a function of t


the early voting rate and the Election Day turnout rate. The question for this model is how early information

about the advanced voting rate is predictive of higher total turnout, both mechanically so (as advanced votes

count toward total turnout), and as a barometer that Election Day voting may be higher in the election (i.e.,

evidence of election intensity). Consider the following model:

##### Dt Rt â At At
 Vt = Rt [ + ] = Rt [dt (1 â at ) + at ] Rt â At Rt Rt


at = A /t Rt and d =t Dt /(R ât A )t . The variables Rt and at are observed; measure dt using the prior

election.

In practice, we estimate this model similar to the previous models, first estimating the relationship between

advanced vote and total vote in a prior election then fitting that to the next election. We also demonstrate the

capacity to combine advanced vote information with other models (particularly Registration and Lagged Vote

Models).

##### Vg,t = Î±(t) + Î²(t)Ag,t + Ïµ(gt) (2.9)

We then predict turnout in the next election through the following model:

##### V[^]g,t+1 = Î±^[(][t][)] + Î²[^][(][t][)]Ag,t+1 (2.10)

### 2.2. Data

To estimate each of these models, we developed a database of registration, turnout, election results, and

demographics at the county and CD level in the United States in 2012, 2016, and 2020. These data were

[provided by the CBS Decision Desk and MIT Election Lab, as supplemented with election results data](https://electionlab.mit.edu/data)

collected directly from states. The data consist of county and congressional House district election results for

presidential elections 2012, 2016, and 2020. For each county and district, we observe the total number of

registered voters in that geographic unit on Election Day, the total number of votes cast, presidential vote share,

and congressional vote share. We combine these data with data from the 2016 and 2020 Election

Administration and Voting Survey, which provides information on total advanced vote as of Election Day for


-----

the 2016 and 2020 elections.[5] Figure 1 shows the turnout rate among registered voters by county for the 2012,

2016, and 2020 elections.

###### Figure 1. Turnout among registered voters across counties, 2012â2020. Maps plot the
 turnout rate among registered voters by county for the 2012, 2016, and 2020 elections.

In our analysis, we focus on predicting total votes rather than turnout rate. We do so for three reasons. First, for

turnout rate, we do not know what the denominator should be. Is it votes as a percent of voting age population?

Of citizen voting age population? Of population? Second, the available population numbers are themselves

lagged, not contemporary. The census does not provide an estimate of population as of October of the election

year; they release that estimate a year later. Dividing by lagged population adds error in that some places are

growing faster than others. Third, on election night, we are trying to estimate totals: How many votes are

expected compared to how many are in. Adding a denominator might add other noise to the modeling. Citizen

voting age population, for example, is an estimate with its own noise.

We further combine these data with information from the 2006â2010, the 2010â2014, and the 2014â2018

[American Community Survey (ACS) from the United States Census. From these data we source the](http://www.nhgis.org/)

demographic variables used in the estimation of the Demographic Model. We use the 2006â2010 ACS to

measure demographic variables for the 2012 presidential election, the 2010â2014 ACS for the 2016

presidential election, and the 2014â2018 ACS for the 2020 presidential election. We do use these earlier ACS

data for each election since at the time of any given election, the more recent (i.e., 2015 or 2016 ACS

information for the 2016 election) is either not yet released or is still being collected. The demographic

variables we use from the ACS include total county and district population, the percentage of the population in

a county or district that is married, graduated from college, the median household income, the percentage of the

population that is White, Black, and Hispanic, and the percentage of the population in each of four age

categories: 15â24, 25â34, 35â64, and above 65 years of age.

### 2.3. Estimation and Estimates

To estimate the Registration Model, we first subset our data by state, and estimate separate models within each

state. For each state, we estimate regressions in the form of Equation 2.1 on the 2012 results and the 2016


-----

election results, modeling turnout totals in each election as a function of registration totals in each election. We

do so for both counties and districts, separately, as the units of analysis. We then apply the coefficients from

these regression models to predict turnout in the next presidential election. So with the 2012 regression

parameters we predict 2016 turnout using 2016 registration, and the 2016 regression parameters we predict

2020 turnout using 2020 registration.

To estimate the Lagged Vote Model, we conduct a similar exercise, except that we fit regressions for each state

measuring the relationships between 2012 turnout and 2016 turnout, and then use those parameters to predict

2020 turnout using 2016 turnout.

We estimate the Demographic and the Early Vote Models following a similar approach to the Registration

Model. We use regression analyses using data from 2012 to estimate the parameters of these models. We then

predict 2016 turnout. Likewise, we perform regressions for the 2016 data and use that to predict 2020 turnout.

The Early Vote Model is only estimated on counties, since EAVS does not have early vote data aggregated by

congressional districts.

To estimate the Competition Model, which uses lagged vote margin, we use 2012â2016 data to estimate

regressions we then use to predict on test data from 2016â2020. The Competition Model is only estimated at

the district level, since competition is operationalized through the lagged vote margin of previous House of

Representative elections at the district level. Our main results use weighted ordinary least squares regressions,

using the number of registered voters in a county or geography as weights.

Figure 1 plots the coefficients across models. For both the county models and the district models, and across

years, the registration coefficients are clustered around 0.8 and 0.9 respectively, ranging from â0.139 to 1.46

for counties and â0.442 to 6.59 for districts. This means that on average across states and models, each

additional registrant in a county or district translates into 0.8â.0.9 additional votes in that county/district in that

election. The lagged vote coefficients range from 0.429 to 1.19 for counties (0.608 to 7.63 for districts), and are

generally clustered around 1, indicative of the strong likelihood that a voter in a past election will vote in the

next election. The Demographic Model yields many coefficients, so Figure 2 only shows the distribution of

coefficients for percent White.[6] These coefficients have a wide range, but on average are not predictive of

increased or decreased turnout in a county or district, net of other variables in the Demographic Model. The

early vote coefficients range from 0.83 to 31.84, but are generally concentrated between 0.83 and 5,

demonstrating a strong positive relationship between early vote counts and total vote counts. This positive

correlation is in part mechanical, since each additional early vote equates to an additional total vote. But the

extent this coefficient varies in size is a function of whether the early vote is a substitution for Election Day

turnout or a sign of heightened participatory interest in the election. The coefficients for the Competition

Model, lagged vote margin at the district level (ranging from 0 to 1), are centered close to 0 but range widely.


-----

###### Figure 2. Coefficients from state subsets across models.

## 3. Comparison of Models

We compare the predictive performance of the models using the bias and root mean squared errors (RMSE) of

the predictions. Table 1 reports these performance statistics for the Registration and Lagged Vote Models.[7] We

report bias and RMSE in total vote counts and as a percentage of average county or district level vote totals.

The Registration Model at county level predicts 2016 turnout using 2012 training data with a bias of â2.4%,

and predicts 2020 turnout using 2016 training data with a bias of 5.6%. The RMSE for the 2016 turnout

prediction is 42%, while the RMSE for the 2020 turnout prediction is 29.1%. The district models show

improved performance, with biases of â2.2% (2016 turnout) and 0.8% (2020 turnout). The RMSE for these

estimates are 11.1% (2016 turnout) and 12% (2020 turnout). The Lagged Vote Model exhibits lower variance,

but overall greater absolute bias than the Registration Model. Predicting 2020 turnout using 2012-2016 training

data at the county-level with the Lagged Vote Model has a bias of â4.3% and a RMSE of 23.9%. The district
level prediction performs worse, with a bias of â9.7% but a RMSE of just 11.7%.

Table 1. Evaluation of Registration and Lagged Vote Models.


-----

|Col1|Registration|Col3|Col4|Col5|Lagged Vote|Col7|
|---|---|---|---|---|---|---|
||County||District||County|District|
|Training|2012|2016|2012|2016|2012-2016|2012-2016|
|Test|2016|2020|2016|2020|2016-2020|2016-2020|
|Bias (Total)|â1,065|2,803|â6,884|3,058|â2,171|â35,275|
|Bias (% of Avg. Vote)|â2.4%|5.6%|â2.2%|0.8%|â4.3%|â9.7%|
|RMSE (Total)|18,436|14,564|34,589|43,574|11,983|42,450|
|RMSE (% of Avg. Vote)|42%|29.1%|11.1%|12%|23.9%|11.7%|
|Units (Train)|3,151|3,151|377|428|3,151|377|
|States (Train)|50|50|40|43|50|40|
|Units (Test)|3,151|3,151|377|428|3,151|377|
|States (Test)|50|50|40|43|50|40|


In the appendix, we present alternative versions of the Registration and Lagged Vote Models where we logged

the outcome, total votes, and the predictors, registration or lagged votes. Table A1 presents the bias and RMSE

from these models. The table reports these statistics in terms of total votes so as to be most comparable to the

models in the manuscript, but the underlying models use logged variables. We find that the logged models

perform very similarly to the unlogged models, in terms of both bias and RMSE. The logged registration model

is worse for counties in 2016 (bias of â4.5% compared to 2.4% for the unlogged model), but better in 2020

(0.1% compared to 5.6% bias). For districts, the logged registration model is slightly worse (â2.3% versus

â2.2% and 1.7% versus 0.8% for 2016 and 2020, respectively) than the unlogged versions of the models. The

Lagged Vote Model is more biased (â6% versus â4.3%) for counties and shows essentially the same bias

(â9.7%) for districts.

Table 2 presents the performance metrics for the Demographic Model, Early Vote Model, and the Competition

Model.[8] The Demographic Model at the county level offers similar performance to the Registration Model in

terms of bias, but suffers from higher RMSE. Predicting 2016 county turnout using 2012 training data using

the Demographic Model results in a bias of 2.7% and a RMSE of 60%. For the 2020 county turnout prediction,

the bias is â4% and the RMSE is 68.8%. The district predictions are more uneven, with the 2016 turnout


-----

prediction performing very wellâwith a bias of â0.1%, although a RMSE of 43.6%âbut the 2020 prediction

performs poorly, showing a bias of â13.2% (although its RMSE is just 24.5%). Overall, the Demographic

Model can predict turnout well, but is more uneven across elections in its performance than the Registration

Model. Further, the RMSE from the Demographic Model is always higher than that for the Registration Model,

so while biases of the two models may be similar at times, the Demographic Model often offers higher

uncertainty in its forecasts.

Table 2. Evaluation of Demographic, Early Vote, and Competition Models.

**Demographics** **Early Vote** **Competition**

**County** **District** **County** **District**

Training 2012 2016 2012 2016 2012 2016 2012-2016

Test 2016 2020 2016 2020 2016 2020 2016-2020

Bias (Total) 1,181 â1,985 â255 â47,882 10,839 55,286 â5,636

Bias (% of 2.7% â4% â0.1% â13.2% 24.7% 110.3% â1.6%

Avg. Vote)

RMSE (Total) 26,349 34,487 135,841 88,773 128,697 317,304 262,075

RMSE (% of 60% 68.8% 43.6% 24.5% 292.9% 633% 72.2%

Avg. Vote)

Units (Train) 3,110 3,110 365 426 2,883 2,873 425

States (Train) 49 49 40 43 45 46 43

Units (Test) 3,110 3,110 365 426 2,865 2,936 428

States (Test) 49 49 40 43 45 46 43

The Early Vote Model has very high bias and RMSE. Predicting 2016 turnout using 2012 training data at the

county level with the Early Vote Model has a bias of 24.7% and a RMSE of 292.9%. For the 2020 turnout

prediction, these metrics are even worse, with a bias of 110.3% and a RMSE of 633%. Thus, these predictions

show both high bias and uncertainty, and Early Vote is not a reliable predictor on its own of total vote counts.

The Competition Model does much better, with a bias of â1.6% for predicting 2020 turnout using 2012â2016

training data, which is almost as low as the equivalent district-level bias (0.8%) for predicting 2020 turnout

|Col1|Demographics|Col3|Col4|Col5|Early Vote|Col7|Competition|
|---|---|---|---|---|---|---|---|
||County||District||County||District|
|Training|2012|2016|2012|2016|2012|2016|2012-2016|
|Test|2016|2020|2016|2020|2016|2020|2016-2020|
|Bias (Total)|1,181|â1,985|â255|â47,882|10,839|55,286|â5,636|
|Bias (% of Avg. Vote)|2.7%|â4%|â0.1%|â13.2%|24.7%|110.3%|â1.6%|
|RMSE (Total)|26,349|34,487|135,841|88,773|128,697|317,304|262,075|
|RMSE (% of Avg. Vote)|60%|68.8%|43.6%|24.5%|292.9%|633%|72.2%|
|Units (Train)|3,110|3,110|365|426|2,883|2,873|425|
|States (Train)|49|49|40|43|45|46|43|
|Units (Test)|3,110|3,110|365|426|2,865|2,936|428|
|States (Test)|49|49|40|43|45|46|43|


-----

with the Registration Model. However, the Competition Model does show a higher RMSE than the

Registration Model, with a RMSE of 72.2%.

The evaluation of each individual model indicates that the Registration Model is the most consistently accurate

of the models. The Demographic and Competition Models are competitive with the Registration Model in

terms of minimizing bias, but those models show higher variance and thus larger RMSE than the Registration

Model. As a result, the standard error of predictions of turnout forecasts based on Demographic or on Electoral

Competition will always be larger than predictions that rely on Registration rates. For election administrators,

this would mean higher cost in terms of the amount of ballots, precincts, and the like that need to be prepared

in order to guard against a very high turnout election in some areas. For analysts on election night, it means a

much slower rate at which models will converge on a forecast on which a final call might be made. For

academic researchers comparing an observed election outcome versus a counterfactual, it means greater

uncertainty about what that counterfactual might be, and lower statistical power (and more errors in academic

judgment) about the effects of innovations in election administration.

Next, we present scatterplots to provide visual evidence of the predictive performance of each model. Figure 3

plots state-level predictive vote counts against actual vote counts for each model (Registration, Lagged Vote,

Demographic, Early Vote, and Competition) for relevant election years and across counties and districts.

The scatterplots show that the Registration Model predicts state vote totals across years and geographies well.

It slightly understates 2016 turnout (using 2012 parameters) and slightly overstates 2020 turnout (using 2016

parameters). We are particularly surprised by the performance of the model in 2020 given the substantial

changes in the electoral procedures in the states and the challenges people faced voting during the COVID-19

pandemic.

The Lagged Vote Model performed somewhat less well than the Registration Model. Lagged Vote tends to

understate turnout, but overall the predicted and actual state totals show high correspondence.

Similarly, the Demographic Model shows high correspondence between the actual and observed vote, but a

tendency to understate predicted turnout. Lagged Vote and Demographic fail to capture upward trending in

turnout.

The Early Vote Model does not perform well. It dramatically overpredicts turnout in many states, and did a

particularly poor job in Pennsylvania, Kentucky, and New York in the 2020 elections.

The Competition Model on average overstates turnout but overall performs well, with most predicted and

actual totals close in most states. It has much larger deviations in the largest states, such as Texas and

California.


-----

The models perform generally better when data are measured at the congressional district level, rather than the

county level. This is important because elections are administered at the county level, and much of the data

reporting and analyses use the county as the level of analysis. We return to the question of why these

differences arise at the end of this article.

###### Figure 3. Predicted votes against total votes across models.

The final model examined combines these approaches. Political scientists and sociologists studying turnout

frequently combine many, if not all, of the approaches into a single analysis. Often the effort is to conduct a

horse race to find the most powerful explanatory account or to attribute portions of the explained variance to

each of the different accounts (e.g., Rosenstone and Hansen, 1993). Rosenstone and Hansen (1993) expressly

use a regression model that combines these many approaches in a single cross-sectional analysis to explain

changes in the level of turnout in the United States from 1960 to 1990.

How well does such an approach work for our problem? We took the Registration Model as the baseline model

and then added each of the others (one at at time) to it. We also combined all of the models into one âsuper

model.â Thus, we first assess four additional models, the first combining registration and lagged vote covariates

in the same regression, the second combining registration and demographic variables, the third using

registration and early vote, and the fourth with registration and lagged vote margin. For each combined model,

we estimate it in a similar fashion as the individual models: subsetting the data by state and running county unit

or district unit models for each state across relevant time periods, predicting 2016 turnout using 2012 training

data and 2020 turnout using 2016 training data where appropriate. Finally, we put all of the models into one

saturated model. The bias and RMSE of each of these combined models are reported in Tables 3 and 4.


-----

When we combine the Registration Model with the Lagged Vote Model, we predict 2020 county turnout using

2012â2016 training data with a bias of â2.4% and a RMSE of â23.9%. District turnout in 2020 with this

combined model is predicted with a bias of â7.3% and a RMSE of 11.3%. The district turnout models show

greater absolute bias than the stand-alone registration model, although the RMSE is similar. Thus, there seems

to be perhaps some prediction gains from combining election year registration information with lagged vote

information.

Combining the Registration and Demographic Models results in low bias for the county-level models in

predicting both 2016 and 2020 turnout (â4.1% and â1.7% bias, respectively). This combined model

outperforms the stand-alone Registration and Demographic Models in terms of absolute bias in predicting 2020

county turnout but not 2016 county turnout. The RMSE for the combined model county estimates are 54.9%

and 58.4%. Thus, adding these additional variables increased the RMSE, relative to the stand-alone

Registration county models.

Worse still are the forecasts conducted using Registration plus Demographic using data at the congressional

district level. The biases for these models leap up to the double digits in predicting 2016 and 2020 turnout. The

RMSE for these district estimates are 287% in predicting 2016 turnout and 26.5% in predicting 2020 turnout.

The combined Registration and Early Vote Models perform well in predicting 2016 county turnout using 2012

training data (â1.4% bias and 33.9% RMSE) but perform poorly when predicting 2020 county turnout using

2016 training data (16.6% bias and 150.1% RMSE). The combined Registration and Competition Models[9]

perform perhaps the strongest of any model, stand-alone or combined. This combined model predicts 2020

district turnout using 2012â2016 training data with a bias of just â0.5% and a RMSE of 10.2%. This represents

a reduction in bias and RMSE compared to the stand-alone Registration Model and a reduction compared to

the stand-alone Competition Model.The success of this model highlights the potential for registration

information and electoral competition information to provide complementary information in forecasting

turnout.

Table 3. Evaluation of Registration Model combined with other models.

|Col1|+ Lagged Vote|Col3|+ Demographics|Col5|Col6|Col7|+ Early Vote|Col9|+Competit ion|
|---|---|---|---|---|---|---|---|---|---|
|Registrati on|County|District|County||District||County||District|
|Training|2012-2016|2012-2016|2012|2016|2012|2016|2012|2016|2012-2016|
|Test|2016-2020|2016-2020|2016|2020|2016|2020|2016|2020|2016-2020|


-----

|Bias (Total)|â1,189|â26,527|â1,780|â833|57,451|â40,433|â621|8,344|â1,830|
|---|---|---|---|---|---|---|---|---|---|
|Bias (% of Avg. Vote)|â2.4%|â7.3%|â4.1%|â1.7%|18.5%|â11.1%|â1.4%|16.6%|â0.5%|
|RMSE (Total)|12,003|41,032|24,105|29,273|893,474|96,349|14,895|75,227|36,922|
|RMSE (% of Avg. Vote)|23.9%|11.3%|54.9%|58.4%|287%|26.5%|33.9%|150.1%|10.2%|
|Units (Train)|3,151|377|3,110|3,110|365|426|2,919|2,873|428|
|States (Train)|50|40|49|49|40|43|46|46|43|
|Units (Test)|3,151|367|3,111|3,111|377|428|2,865|2,936|418|
|States (Test)|50|40|49|49|40|43|46|46|43|


Table 4. Evaluation of all models combined.

|Col1|+ Lagged Vote|+ Lagged Vote|
|---|---|---|
||+ Demographics|+ Demographics|
||+ Early Vote|+ Competition|
|Registration|County|District|
|Training|2012-2016|2012-2016|
|Test|2016-2020|2016-2020|
|Bias (Total)|â2,311|â36,322|
|Bias (% of Avg. Vote)|â4.6%|â10%|


-----

|RMSE (Total)|33,308|87,272|
|---|---|---|
|RMSE (% of Avg. Vote)|66.4%|24%|
|Units (Train)|2,873|375|
|States (Train)|46|40|
|Units (Test)|2,936|377|
|States (Test)|46|40|


Adding additional variables to the basic Registration Model, then, rarely reduced bias or RMSE. The clearest

evidence of this is in Table 4, which reports performance statistics for the saturated model combining all five

approaches. This model shows similar bias to the stand-alone Registration Model for counties but much higher

RMSE. For districts, both bias and RMSE are substantially higher than the Registration Model. In part this is

because the Registration Model is itself a fairly good forecasting model, so it is challenging to improve on it.

The bigger lesson is that complex models that combine many different approaches and elements are often

overfitting the data. This can only be evident when looking at the predictive value of the analyses, rather than

simply the fit of the models within samples. We think this is a very important lesson not only for the

forecasting literature but for the entire empirical enterprise that attempts to explain why people vote.

## 4. Extensions

Two aspects of this analysis deserve further immediate attention. First, we can validate this analysis by

examining a simple prediction implied by the results here. The prediction is this. Fluctuations in aggregate

turnout over time at the national level ought to follow the Registration Model. Second, there is an internal

puzzle that deserves further discussion: Why are predictions based on congressional districtâlevel data better

than predictions based on county-level data?

### 4.1. The Registration Model Over Time Using CPS

One way to test the value of the Registration Model is to see how well it explains trends in turnout rates over

time. As is well-known among political scientists, turnout in the United States fell from 1960 to 2000, and it

has increased since 2000. Does the Registration Model explain long-term patterns in turnout?

There is no national measure of total registered voters in the United States based on voter files, because

national voter files became available only in 2008. Research on historical registration rates relies, instead, on

the Current Population Study (CPS) data from 1970 to the present. Below are the CPS estimates of registration

and turnout among citizens and turnout among registered voters. Several scholars have criticized these data as

being slightly inaccurate, particularly for some demographics (Ansolabehere et al., 2022; Ghitza & Gelman,


-----

2020).[10] Although not perfect, these are the best available data on registration and turnout over the past 50

years. We use the estimates as reported by CPS for each year. It may be possible to improve the estimates by

applying different weights,[11] but we take the data as given and assume that, even if it is off by a couple of

percentage points in the levels, that it reflects trends.

Table 5. Registration and turnout 1970â2020, Current Population Survey.

Election Cycle

CPS Category Presidential Midterm

**Average** **Average**

(SD) (SD)

Share of Citizens Who Report Being **71.9** **67.0**

Registered to Vote (1.6) (1.3)

Share of Registered People Who Report **87.7** **71.6**

That They Voted (2.5) (4.0)

Share of Citizens Who Report Report That **63.1** **48.0**

They Voted (2.8) (3.2)

_Note. Table reports averages and standard deviations across presidential and midterm election years from 1970 to 2020._

We apply the model to the CPS data at the national level. For each year, we calculate the predicted turnout as

the registration rate times the turnout rate of registered voters in the prior presidential year for presidential

elections or the prior midterm year for midterm elections. For instance, the predicted turnout in 2020 equals the

voting age population times the CPS estimate of turnout as a percent of registered voters in 2016 and multiply

that times the registered percent in 2020.

##### T1 = (T0 /R0 )R1

The model does surprisingly well. We calculated the percentage error of the estimated total turnout: the actual

turnout in a year minus the modelâs predicted turnout, divided by the actual turnout. The percentage error

averages â.0009, with a standard deviation of .059. That is, on average there is no bias in the Registration

Modelâs predicted turnout over time, and its mean squared error is about 6%. According to the CPS report on

âVoting and Registrationâ for 2022 (U.S. Census Bureau, 2022), the standard error on the survey estimate is

approximately 1%.[12] The survey standard error is independent of the model standard error, so the model

standard error is approximately 5% and the survey standard error adds another 1%.

|Col1|Election Cycle|Col3|
|---|---|---|
|CPS Category|Presidential|Midterm|
||Average (SD)|Average (SD)|
|Share of Citizens Who Report Being Registered to Vote|71.9 (1.6)|67.0 (1.3)|
||||
|Share of Registered People Who Report That They Voted|87.7 (2.5)|71.6 (4.0)|
||||
|Share of Citizens Who Report Report That They Voted|63.1 (2.8)|48.0 (3.2)|


-----

The model misses substantially in two years, 1974 and 2018. Both are midterm elections. The percent error is

â12% in 1974 and +18% in 2018. These could reflect shifts in the electorate, or changes in the survey, as the

CPS implemented the correction suggested by Hur and Achen (2013).

The mean squared error reveals that there is excess error due to the model. Among the 13 presidential elections

analyzed, the average error is â.0003 with a standard deviation of .043, substantially lower than the entire

sample of observations. If one assumes independent predicted values, the expected variation is approximately

1%. The standard deviation of the 13 presidential predictions is .32; hence, the standard error is .01 (i.e.,


#### .032/ 13


). This is an apples-to-apples comparison as the turnout predictions for presidential elections are


based on lagged presidential election years. The observed mean squared error of .04 is larger, and suggests that

modeling error explains much of the inaccuracy of the model. The modeling errors, however, are not

systematically over- or underestimating turnout. Similarly, among the 13 midterm elections analyzed, the

average error is â.0016 with a standard deviation of .074, much larger than the prediction errors for the

presidential elections. Among the midterm elections, the variance of the predicted value is .039 in the 13

midterm years, which implies a standard error on the forecast of .011. The observed variance of the deviation

of forecasts from the true values is .07 in midterm elections.

It is unclear to us whether further improvements are possible at this level of analysis. Although the standard

error exceeds sampling error, it is unclear if refinements could reduce that error further. The Registration

Model is very parsimonious, and only uses the degree of freedom lost by estimating turnout rates from lagged

observations. Other corrections, such as for demographics, would use more information and thus more degrees

of freedom. Our analysis of the CD-level data in 2016 and 2020 suggests that combining demographics with

the Registration Model led to overfitting and actually worsened prediction accuracy.

The Registration Model shows no evidence of bias in its predictions about the national trends in total turnout

since 1970. This fact carries an interesting substantive result. The long-term drop in turnout from 1960 to 2000

and the rebound that has occurred in the 21st century may be accounted for by fluctuations in voter registration

alone. In the late 1990s the United States implemented the National Voter Registration Act (NVRA, 1993), and

in the early 2000s the parties began aggressive voter mobilization campaigns. It is plausible that the legal

innovations of the NVRA provided the incentives for people to get registered and for campaign organizations

to facilitate that. The result may have been a steady increase in registration, which translated into increased

turnout rates.

### 4.2. Counties Versus CDs and the Problem of Heterogeneity

One puzzle resulting from our analysis is the difference between the models fitted using congressional districtâ

level data and county-level data. Most research and analytics use county-level data. Most of the analytic tools

used by survey research firms and media organizations rely on county-level data and estimates. Why are the

predictions using the county-level data worse than those derived using the CD-level data?


-----

The sheer number of units would lead one to think that parameter estimates based on counties should be

superior. There are more than 3,100 counties, but only 435 congressional districts. Yet, consider the estimates

in Table 1. The biases for the Registration Model and the RMSE are lower using the CD-level data than using

the county-level data. The larger number of counties does not lead to higher precision in the prediction

estimator.

How is that possible? We conjecture that the problem arises from across-unit heterogeneity. Congressional

districts are all the same size, roughly 700,000 people. Counties vary considerably, from a few hundred (e.g.,

Loving County, Texas, Arthur County, Nebraska, and Petroleum County, Montana) to nearly 10 million people

in Los Angeles County, California. Los Angeles County has a total population equal to the combined

population of the nine least populous states. It is this variation in population size that seems to be the problem.

More correctly, the turnout rate of registered voters varies randomly, but because of the extremely different unit

sizes, the variation becomes correlated with unit size. This is not readily corrected by simply reweighting the

data by population, as the error in the county appears to be correlated in a non-ignorable way.

That problem is less present in the CD-level data. Even though there are many fewer CDs than counties, their

populations are, as a matter of law, nearly equal. The heterogeneity in turnout rates among registered voters

cannot be correlated with unit population size in the CD-level data, because the CD populations are all virtually

the same.

Future research could try models using both counties and congressional districts together, to try and interrogate

discrepancies in accuracy by geographic unit. Additionally, a nested model that looks at counties that are

smaller than congressional districts might further be useful in testing the hypotheses presented in this section.

## 5. Conclusion

The narrow implication of this analysis is that forecasting turnout boils down to understanding the number of

people who are on the voter rolls, and thus eligible to vote, and the turnout rate among registered voters. Those

two factors, combined, yield a parsimonious model and accurate predictor of turnout at the CD, state, and

national levels. Other models, such as those that rely on demographics, lagged vote, or competition, or

combinations of models, tend to perform less well in the sense that they have higher prediction root mean

squared error.

The broader lesson, though, is that prediction should inform the more general enterprise of social science

analysis. Too often, political scientists, sociologists, economists, and other social scientists rely on model fit

within a particular sample to test theories and analyze their empirical implications. That practice, as shown in

the case of turnout, leads to overfitting. A model might seem compelling within the data under study, but when

we use it to look forward, we quickly find that it does not yield particularly useful predictions. Often,

researchers have loaded regression analyses with many variables. That is especially true when the researchers


-----

are attempting to run a horse race among competing models or approaches to understanding a problem. The

results here should give all researchers pause about that particular approach to inquiry.

The approach we recommend is to use explanatory models in tandem with predictive analyses. In the analysis

of turnout, that approach lands us back with one of the early, significant results in the literature: The finding

from Wolfinger and Rosenstone (1980) that registration was the key to explaining turnout. We find that is not

only true in an analysis of what factors correlate most strongly with turnout, but which model yields the best

predictions of future turnout. The results here also offer a cautionary tale. At least in the context examined in

this articleâforecasting turnout on election nightâpolitical scientists may have leaned too hard on their data

when estimating highly saturated regression models. We should give such analyses greater weight only when

they can demonstrate their predictive power, as well as the strength of correlations or causal effects. Saturated

models may be more useful when the goal is understanding variation in political variables across demographic

groups or geographies (Ghitza & Gelman, 2013; Trangucci et al., 2018), but from our analysis they appear

limited for understanding geographic turnout for election-night forecasting.

## Disclosure Statement

Stephen Ansolabehere, Jacob Brown, Kabir Khanna, Connor Phillips, and Charles Stewart III have no financial

or non-financial disclosures to share for this article.

References

Ansolabehere, S., Fraga, B. L., & Schaffner, B. F. (2022). The Current Population Survey voting and

registration supplement overstates minority turnout. The Journal of Politics, 84(3), 1850â1855.

[https://doi.org/10.1086/717260](https://doi.org/10.1086/717260)

Ansolabehere, S., Hersh, E., & Shepsle, K. (2012). Movers, stayers, and registration: Why age is correlated

with registration in the U.S. Quarterly Journal of Political Science, 7(4), 333â363.

[https://doi.org/10.1561/100.00011112](https://doi.org/10.1561/100.00011112)

Blais, A. (2006). What affects voter turnout? Annual Review of Political Science, 9, 111â125.

[https://doi.org/10.1146/annurev.polisci.9.070204.105121](https://doi.org/10.1146/annurev.polisci.9.070204.105121)

Brady, H. E., Verba, S., & Schlozman, K. L. (1995). Beyond SES: A resource model of political participation.

_[American Political Science Review, 89(2), 271â294. https://doi.org/10.2307/2082425](https://doi.org/10.2307/2082425)_

Burden, B. C., & Stewart, C. III. (2014). The measure of American elections. Cambridge University Press.

Burden, B. C., Canon, D. T., Mayer, K. R., & Moynihan, D. P. (2014). Election laws, mobilization, and

turnout: The unanticipated consequences of election reform. American Journal of Political Science, 58(1), 95â


-----

[109. https://doi.org/10.1111/ajps.12063](https://doi.org/10.1111/ajps.12063)

Burnham, W. D. (1974). Theory and voting research: Some reflections on Converseâs âchange in the American

[electorate.â American Political Science Review, 68(3), 1002â1023. https://doi.org/10.2307/1959143](https://doi.org/10.2307/1959143)

Cantoni, E., & Pons, V. (2021). Strict Id laws donât stop voters: Evidence from a U.S. nationwide panel, 2008â

[2018. The Quarterly Journal of Economics, 136(4), 2615â2660. https://doi.](https://doi.org/10.1093/qje/qjab019) [org/10.1093/qje/qjab019](https://doi.org/10.1093/qje/qjab019)

Cantoni, E., & Pons, V. (2022). Does context outweigh individual characteristics in driving voting behavior?

Evidence from relocations within the U.S. American Economic Review, 112(4), 1226â1272.

[https://doi.org/10.1257/aer.20201660](https://doi.org/10.1257/aer.20201660)

Clark, W. R., & Golder, M. (2015). Big data, causal inference, and formal theory: Contradictory trends in

[political science? PS: Political Science & Politics, 48(1), 65â70. https://doi.org/10.1017/S1049096514001759](https://doi.org/10.1017/S1049096514001759)

Converse, P. E. (1972). Change in the American electorate. In A. Campbell, & P. E. Converse (Eds.), The

_human meaning of social change (pp. 263â337). Russell Sage Foundation._

Corasaniti, N. (2021, December 29). Voting rights and the battle over elections: What to know. The New York

_[Times. https://www.nytimes.com/article/voting-rights-tracker.html](https://www.nytimes.com/article/voting-rights-tracker.html)_

Dowding, K. (2021). Why forecast? The value of forecasting to political science. PS: Political Science &

_[Politics, 54(1), 104â106. https://doi.org/10.1017/S104909652000133X](https://doi.org/10.1017/S104909652000133X)_

Dowding, K., & Miller, C. (2019). On prediction in political science. European Journal of Political Research,

_[58(3), 1001â1018. https://doi.org/10.1111/1475-6765.12319](https://doi.org/10.1111/1475-6765.12319)_

Enos, R. D., & Fowler, A. (2014). Pivotality and turnout: Evidence from a field experiment in the aftermath of

[a tied election. Political Science Research and Methods, 2(2), 309â319. https://doi.org/10.1017/psrm.2014.5](https://doi.org/10.1017/psrm.2014.5)

Forster, M. R. (2002). Predictive accuracy as an achievable goal of science. Philosophy of Science, 69(S3),

[S124âS134. https://doi.org/10.1086/341840](https://doi.org/10.1086/341840)

Fowler, A. (2015). Regular voters, marginal voters and the electoral effects of turnout. Political Science

_[Research and Methods, 3(2), 205â219. https://doi.org/10.1017/psrm.2015.18](https://doi.org/10.1017/psrm.2015.18)_

Fowler, J. H., & Dawes, C. T. (2008). Two genes predict voter turnout. The Journal of Politics, 70(3), 579â594.

[https://doi.org/10.1017/S0022381608080638](https://doi.org/10.1017/S0022381608080638)

Fraga, B. L. (2018). The turnout gap: Race, ethnicity, and political inequality in a diversifying America.

Cambridge University Press.


-----

Fraga, B. L., & Hersh, E. D. (2018). Are Americans stuck in uncompetitive enclaves? An appraisal of U.S.

electoral competition. Quarterly Journal of Political Science, 13(3), 291â311.

[https://doi.org/10.1561/100.00017161](https://doi.org/10.1561/100.00017161)

Gerber, A. S., Green, D. P., & Shachar, R. (2003). Voting may be habit-forming: Evidence from a randomized

[field experiment. American Journal of Political Science, 47(3), 540â550. https://doi.org/10.2307/3186114](https://doi.org/10.2307/3186114)

Ghitza, Y., & Gelman, A. (2013). Deep interactions with MRP: Election turnout and voting patterns among

small electoral subgroups. American Journal of Political Science, 57(3), 762â776.

[https://doi.org/10.1111/ajps.12004](https://doi.org/10.1111/ajps.12004)

Ghitza, Y., & Gelman, A. (2020). Voter registration databases and MRP: Toward the use of large-scale

[databases in public opinion research. Political Analysis, 28(4), 507â531. https://doi.org/10.1017/pan.2020.3](https://doi.org/10.1017/pan.2020.3)

Green, D. P., & Gerber, A. S. (2004). Get out the vote!: How to increase voter turnout. Brookings Institution

Press.

Grimmer, J. (2015). We are all social scientists now: How big data, machine learning, and causal inference

[work together. PS: Political Science & Politics, 48(1), 80â83. https://doi.org/10.1017/S1049096514001784](https://doi.org/10.1017/S1049096514001784)

Hersh, E. (2015). Hacking the electorate: How campaigns perceive voters. Cambridge University Press.

Hur, A., & Achen, C. H. (2013). Coding voter turnout responses in the current population survey. Public

_[Opinion Quarterly, 77(4), 985â993. https://doi.org/10.1093/poq/nft042](https://doi.org/10.1093/poq/nft042)_

Leighley, J., & Nagler, J. (2013). Who votes now?: Demographics, issues, inequality, and turnout in the United

_States. Princeton University Press._

Monroe, B. L., Pan, J., Roberts, M. E., Sen, M., & Sinclair, B. (2015). No! Formal theory, causal inference, and

big data are not contradictory trends in political science. PS: Political Science & Politics, 48(1), 71â74.

[https://doi.org/10.1017/S1049096514001760](https://doi.org/10.1017/S1049096514001760)

National Voter Registration Act of 1993, Pub. L. No. 103-31, 107 Stat. 77 (1993).

[https://www.congress.gov/bill/103rd-congress/house-bill/2](https://www.congress.gov/bill/103rd-congress/house-bill/2)

Olsen, M. E. (1972). Social participation and voting turnout: A multivariate analysis. American Sociological

_[Review, 37(3), 317â333. https://doi.org/10.2307/2093471](https://doi.org/10.2307/2093471)_

Rentsch, A., Schaffner, B. F., & Gross, J. H. (2020). The elusive likely voter: Improving electoral predictions

with more informed vote-propensity models. Public Opinion Quarterly, 83(4), 782â804.

[https://doi.org/10.1093/poq/nfz052](https://doi.org/10.1093/poq/nfz052)


-----

Rosenstone, S. J., & Hansen, J. M. (1993). Mobilization, participation, and democracy in America. Macmillan

Publishing Company.

Rusk, J. G. (1974). Comment: The American electoral universe: Speculation and evidence. American Political

_[Science Review, 68(3), 1028â1049. https://doi.org/10.2307/1959145](https://doi.org/10.2307/1959145)_

Thomsen, D. M. (2023). Competition in congressional elections: Money versus votes. American Political

_Science Review, 117(2), 675â691._

[https://doi.org/10.1017/S0003055422000764](https://doi.org/10.1017/S0003055422000764)

Trangucci, R., Ali, I., Gelman, A., & Rivers, D. (2018). Voting patterns in 2016: Exploration using multilevel

_regression and poststratification (MRP) on pre-election polls. ArXiv._

[https://doi.org/10.48550/arXiv.1802.00842](https://doi.org/10.48550/arXiv.1802.00842)

United States Census Bureau. (2022). Current population survey voting and registration supplement.

[https://www.census.gov/data/datasets/time-series/demo/cps/cps-supp_cps-repwgt/cps-voting.html](https://www.census.gov/data/datasets/time-series/demo/cps/cps-supp_cps-repwgt/cps-voting.html)

Westwood, S. J., Messing, S., & Lelkes, Y. (2020). Projecting confidence: How the probabilistic horse race

[confuses and demobilizes the public. The Journal of Politics, 82(4), 1530â1544. https://doi.org/10.1086/708682](https://doi.org/10.1086/708682)

Wolfinger, R. E., & Rosenstone, S. J. (1980). Who votes? Yale University Press.

Appendix

Table A1. Evaluation of Logged Registration and Lagged Vote Models.

|Col1|Registration|Col3|Col4|Col5|Lagged Vote|Col7|
|---|---|---|---|---|---|---|
||County||District||County|District|
|Training|2012|2016|2012|2012|2012-2016|2012-2016|
|Test|2016|2020|2016|2020|2016-2020|2016-2020|
|Bias (Total)|â1,990|71|â7,153|6,138|â3,026|â35,344|
|Bias (% of Avg. Vote)|â4.5%|0.1%|â2.3%|1.7%|â6%|â9.7%|
|RMSE (Total)|14,381|13,458|34,346|55,643|10,724|43,457|


-----

|RMSE (% of Avg. Vote)|32.7%|26.8%|11%|15.3%|21.4%|12%|
|---|---|---|---|---|---|---|
|Units (Train)|3,151|3,151|377|428|3,151|377|
|States (Train)|50|50|40|43|50|40|
|Units (Test)|3,151|3,151|377|428|3,151|377|
|States (Test)|50|50|40|43|50|40|


_Note: Bias and RMSE in this table are presented in terms of total votes and % of average total vote across counties/districts. This is_

done by generating predictions from the logged model then converting the predictions from logged votes to total votes to aid

interpretation.


-----

-----

Â©2024 Stephen Ansolabehere, Jacob Brown, Kabir Khanna, Connor Phillips, and Charles Stewart III. This

[article is licensed under a Creative Commons Attribution (CC BY 4.0) International license, except where](https://creativecommons.org/licenses/by/4.0/legalcode)

otherwise indicated with respect to particular material included in the article.

Footnotes

1. The models explored in this article are not what CBS uses on election night. Rather, this article explores

components of forecasting models to understand various signals of turnout. â©

2. The leading discussion of these techniques is found in Green and Gerber (2004). â©

3. Perhaps the most sophisticated study to date in this long line of research is Cantoni and Pons (2021). â©

4. We include county or district total population in the estimation of the Demographic and Competition

Models, since the core variables in those models are proportions, while the outcome in all models is total

votes in a county or district. â©

5. Some counties and districts in the data have vote totals that exceed the total number of registrants. These

discrepancies are due to registration counts being current as of the weeks immediately prior to Election Day

for each year, and these cases are disproportionately in states with Election Day registration. We do not

correct these cases in our data, since forecasters of an upcoming election must contend with such data

limitations. â©

6. Figure A1 in the appendix plots the coefficients for all variables in the Demographic Model. â©

7. The district analyses exclude the seven states with only one district (Alaska, Delaware, Montana, North

Dakota, South Dakota, Vermont, and Wyoming). The 2012â2016 district analyses also exclude Virginia,

North Carolina, and Florida due to data availability. â©

8. The county estimates from the Demographic Model exclude Alaska due to data availability. â©

9. When combining the Registration and Competition Models, we omit district population from the

regressions, although it is included in the stand-alone Competition Model as stabilizing covariate since the

model is predicting total votes and lagged vote margin is a proportion. The inclusion of registration counts in

the combined model performs the same role. â©

10. In response to these critiques, the Census Bureau has performed their own evaluation of the accuracy of

the CPS data. See Kurt Bauman, âHow Well Does the Current Population Survey Measure the Composition

of the US Voting Population?" U.S. Census Bureau SEHSD Working Paper 2018-25, July 6, 2018.

[https://www.census.gov/content/dam/Census/library/working-papers/2018/demo/SEHSD-WP2018-25.pdf](https://www.census.gov/content/dam/Census/library/working-papers/2018/demo/SEHSD-WP2018-25.pdf) â©

[11. The weights are available at https://cran.r-project.org/web/packages/cpsvote/vignettes/voting.html](https://cran.r-project.org/web/packages/cpsvote/vignettes/voting.html) â©


-----

[12. See Table 1 of https://www.census.gov/content/dam/Census/library/publications/2022/demo/p20-585.pdf](https://www.census.gov/content/dam/Census/library/publications/2022/demo/p20-585.pdf)

â©

References

Ansolabehere, S., Fraga, B. L., & Schaffner, B. F. (2022). The current population survey voting and

registration supplement overstates minority turnout. The Journal of Politics, 84(3), 1850â1855.

[https://doi.org/10.1086/717260](https://doi.org/10.1086/717260) â©

Ansolabehere, S., Hersh, E., & Shepsle, K. (2012). Movers, stayers, and registration: Why age is correlated

with registration in the U.S. Quarterly Journal of Political Science, 7(4), 333â363.

[https://doi.org/10.1561/100.00011112](https://doi.org/10.1561/100.00011112) â©

Blais, A. (2006). What affects voter turnout? Annual Review of Political Science, 9, 111â125.

[https://doi.org/10.1146/annurev.polisci.9.070204.105121](https://doi.org/10.1146/annurev.polisci.9.070204.105121) â©

Brady, H. E., Verba, S., & Schlozman, K. L. (1995). Beyond SES: A resource model of political

[participation. American Political Science Review, 89(2), 271â294. https://doi.org/10.2307/2082425](https://doi.org/10.2307/2082425) â©

Burden, B. C., & Stewart, C. III. (2014). The measure of american elections. Cambridge University Press. â©

Burden, B. C., Canon, D. T., Mayer, K. R., & Moynihan, D. P. (2014). Election laws, mobilization, and

turnout: The unanticipated consequences of election reform. American Journal of Political Science, 58(1),

[95â109. https://doi.org//10.1111/ajps.12063](https://doi.org//10.1111/ajps.12063) â©

Burnham, W. D. (1974). Theory and voting research: Some reflections on Converseâs âchange in the

American electorate.â American Political Science Review, 68(3), 1002â1023.

[https://doi.org/10.2307/1959143](https://doi.org/10.2307/1959143) â©

Cantoni, E., & Pons, V. (2022). Does context outweigh individual characteristics in driving voting behavior?

Evidence from relocations within the U.S. American Economic Review.

[https://doi.org/10.1257/aer.20201660](https://doi.org/10.1257/aer.20201660) â©

Clark, W. R., & Golder, M. (2015). Big data, causal inference, and formal theory: Contradictory trends in

political science? PS: Political Science & Politics, 48(1), 65â70.

[https://doi.org/10.1017/S1049096514001759](https://doi.org/10.1017/S1049096514001759) â©

Converse, P. E. (1972). Change in the American electorate. In A. Campbell, & P. E. Converse (Eds.), The

_human meaning of social change (pp. 263â337). Russell Sage Foundation._

â©

Corasaniti, N. (2021, December 29). Voting rights and the battle over elections: What to know. The New

_[York Times. https://www.nytimes.com/article/voting-rights-tracker.html](https://www.nytimes.com/article/voting-rights-tracker.html)_

â©

Dowding, K. (2021). Why forecast? The value of forecasting to political science. PS: Political Science &

_[Politics, 54(1), 104â106. https://doi.org/10.1017/S104909652000133X](https://doi.org/10.1017/S104909652000133X)_ â©


-----

Dowding, K., & Miller, C. (2019). On prediction in political science. European Journal of Political

_[Research, 58(3), 1001â1018. https://doi.org/10.1111/1475-6765.12319](https://doi.org/10.1111/1475-6765.12319)_ â©

Enos, R. D., & Fowler, A. (2014). Pivotality and turnout: Evidence from a field experiment in the aftermath

of a tied election. Political Science Research and Methods, 2(02), 309â319.

[https://doi.org/10.1017/psrm.2014.5](https://doi.org/10.1017/psrm.2014.5) â©

Forster, M. R. (2002). Predictive accuracy as an achievable goal of science. Philosophy of Science, 69(S3),

[S124âS134. https://doi.org/10.1086/341840](https://doi.org/10.1086/341840) â©

Fowler, A. (2015). Regular voters, marginal voters and the electoral effects of turnout. Political Science

_[Research and Methods, 3(2), 205â219. https://doi.org/10.1017/psrm.2015.18](https://doi.org/10.1017/psrm.2015.18)_ â©

Fowler, J. H., & Dawes, C. T. (2008). Two genes predict voter turnout. The Journal of Politics, 70(3), 579â

[594. https://doi.org/10.1017/S0022381608080638](https://doi.org/10.1017/S0022381608080638) â©

Fraga, B. L. (2018). The turnout gap: Race, ethnicity, and political inequality in a diversifying America.

Cambridge University Press. â©

Fraga, B. L., & Hersh, E. D. (2018). Are Americans stuck in uncompetitive enclaves? An appraisal of U.S.

electoral competition. Quarterly Journal of Political Science, 13(3), 291â311.

[https://doi.org/10.1561/100.00017161](https://doi.org/10.1561/100.00017161) â©

Gerber, A. S., Green, D. P., & Shachar, R. (2003). Voting may be habit-forming: Evidence from a

randomized field experiment. American Journal of Political Science, 47(3), 540â550. â©

Gerber, A. S., Green, D. P., & Shachar, R. (2003). Voting may be habit-forming: Evidence from a

randomized field experiment. American Journal of Political Science, 47(3), 540â550.

[https://doi.org/10.2307/3186114](https://doi.org/10.2307/3186114) â©

Ghitza, Y., & Gelman, A. (2013). Deep interactions with MRP: Election turnout and voting patterns among

small electoral subgroups. American Journal of Political Science, 57(3), 762â776.

[https://doi.org/10.1111/ajps.12004](https://doi.org/10.1111/ajps.12004) â©

Ghitza, Y., & Gelman, A. (2020). Voter registration databases and MRP: Toward the use of large-scale

[databases in public opinion research. Political Analysis, 28(4), 507â531. https://doi.org/10.1017/pan.2020.3](https://doi.org/10.1017/pan.2020.3)

â©

Grimmer, J. (2015). We are all social scientists now: How big data, machine learning, and causal inference

[work together. PS: Political Science & Politics, 48(1), 80â83. https://doi.org/10.1017/S1049096514001784](https://doi.org/10.1017/S1049096514001784)

â©

Hersh, E. (2015). Hacking the electorate: How campaigns perceive voters. Cambridge University Press. â©

Hur, A., & Achen, C. H. (2013). Coding Voter Turnout Responses in the Current Population Survey. Public

_[Opinion Quarterly, 77(4), 985â993. https://doi.org/10.1093/poq/nft042](https://doi.org/10.1093/poq/nft042)_ â©

Leighley, J. E., & Nagler, J. (2013). Who votes now?: Demographics, issues, inequality, and turnout in the

_United States. Princeton University Press. â©_


-----

Monroe, B. L., Pan, J., Roberts, M. E., Sen, M., & Sinclair, B. (2015). No! Formal theory, causal inference,

and big data are not contradictory trends in political science. PS: Political Science & Politics, 48(1), 71â74.

[https://doi.org/10.1017/S1049096514001760](https://doi.org/10.1017/S1049096514001760) â©

National Voter Registration Act of 1993, Pub. L. No. 103-31, 107 Stat. 77 (1993).

[https://www.congress.gov/bill/103rd-congress/house-bill/2](https://www.congress.gov/bill/103rd-congress/house-bill/2)

â©

Olsen, M. E. (1972). Social participation and voting turnout: A multivariate analysis. American Sociological

_[Review, 37(3), 317â333. https://doi.org/10.2307/2093471](https://doi.org/10.2307/2093471)_ â©

Rentsch, A., Schaffner, B. F., & Gross, J. H. (2020). The elusive likely voter: Improving electoral predictions

with more informed vote-propensity models. Public Opinion Quarterly, 83(4), 782â804.

[https://doi.org/10.1093/poq/nfz052](https://doi.org/10.1093/poq/nfz052) â©

Rosenstone, S. J., & Hansen, J. M. (1993). Mobilization, participation, and democracy in America.

Macmillan Publishing Company.

â©

Rosenstone, S. J., & Hansen, J. M. (1993). Mobilization, participation, and democracy in America.

Macmillan Publishing Company.

â©

Rusk, J. G. (1974). Comment: The american electoral universe: Speculation and evidence. American

_[Political Science Review, 68(3), 1028â1049. https://doi.org/10.2307/1959145](https://doi.org/10.2307/1959145)_ â©

Thomsen, D. M. (2023). Competition in congressional elections: Money versus votes. American Political

_[Science Review, 117(2), 675â691. https://doi.org/10.1017/S0003055422000764](https://doi.org/10.1017/S0003055422000764)_ â©

Trangucci, R., Ali, I., Gelman, A., & Rivers, D. (2018). Voting patterns in 2016: Exploration using

_multilevel regression and poststratification (MRP) on pre-election polls. ArXiv._

[https://doi.org/10.48550/arXiv.1802.00842](https://doi.org/10.48550/arXiv.1802.00842)

â©

United States Census Bureau. (2022). Current population survey voting and registration supplement.

https://www.census.gov/data/datasets/time-series/demo/cps/cps-supp%5Ctextunderscore%7B%7Dcps
repwgt/cps-voting.html â©

Westwood, S. J., Messing, S., & Lelkes, Y. (2020). Projecting confidence: How the probabilistic horse race

confuses and demobilizes the public. The Journal of Politics, 82(4), 1530â1544.

[https://doi.org/10.1086/708682](https://doi.org/10.1086/708682) â©

Wolfinger, R. E., & Rosenstone, S. J. (1980). Who votes? Yale University Press. â©


-----

