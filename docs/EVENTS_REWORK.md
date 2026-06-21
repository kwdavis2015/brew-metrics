# Events Score Updates
Currently the events are scored by users manually entering a point value. We want to refactor this logic so users will only select a WINNER and LOSER team for each event. Specifics listed below. 

## Events Page
- users will select the winning team ONLY for main events
- Best of 3 events will have 3 rounds shown with a team selected as winner for each round 
- events will have a reset option - with a prompt which says "Are you sure?" 
- event point values should be viewable on the page / button entry when an event is selected 

## Admin refactor
- admin events page will have the same logic/flow as regular user events page, with option to override user entry
- manual score entry not required on admin page 

## Scope info
- all events are in scope, except for the Beers Drank, which will refer to the beer counts tracked by users and teams

## Event score reference
- the points per event will be saved to database and retrieved by the application at runtime 

Point Breakdown - Total 1000
* Main events - 400
    * Escanaba - 100
    * Flong round 1 - 50
    * Flong round 2 - 50
    * Keg Race - 100
    * Relay - 100
* Beers Drank - 400
    * 0.4 points per beer
* Misc Events - 200 (best of 3)
    * Friday - 100
        * 20 points
            * Billiards
            * Corn hole
            * Shuffle board
            * Foosball
        * 10 points
            * Darts 
            * Jenga 
    * Saturday - 100
        * 20 points
            * Golf simulator
            * Pool basketball
            * Beersbee
            * Connect 4 
        * 10 points
            * Golden Tee
            * Joust