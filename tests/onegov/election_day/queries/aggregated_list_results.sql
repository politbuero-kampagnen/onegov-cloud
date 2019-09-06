WITH
-- aggregated
agg_election_results AS (
  SELECT
    election_id,
    sum(er.received_ballots) as received_ballots,
    sum(er.eligible_voters) as eligible_voters,

    sum(e.number_of_mandates * (
        er.received_ballots - er.blank_ballots - er.invalid_ballots
            - er.blank_votes - er.invalid_votes)) as accounted_votes
    FROM election_results er LEFT JOIN elections e on er.election_id = e.id
    GROUP BY
             er.election_id

    ),

list_results AS (
    SELECT
        l.election_id,
        l.id,
        number_of_mandates,
        name,
        sum(lr.votes) as votes
    FROM lists l
    LEFT JOIN list_results lr ON l.id = lr.list_id
    GROUP BY
            lr.list_id,
            l.election_id,
            l.id,
            l.number_of_mandates,
            l.name
),

candidate_results as (
    SELECT
           c.election_id,
           c.list_id,
           c.family_name,
           c.first_name,
           sum(cr.votes) as candidate_votes
    FROM candidates c
    LEFT JOIN candidate_results cr on c.id = cr.candidate_id
    GROUP BY
            cr.candidate_id,
            c.election_id,
            c.list_id,
            c.family_name,
            c.first_name
)

-- SELECT * FROM candidate_results;

SELECT
    CASE
        WHEN ar.accounted_votes < 0
            THEN 0
    ELSE ar.accounted_votes
    END as accounted_votes,
    l.election_id,
    l.name,
    l.votes,
    l.number_of_mandates,
    c.family_name,
    c.first_name,
    c.candidate_votes,
    round(l.votes::DECIMAL / ar.accounted_votes, 1) as per_to_total_votes,
    CASE WHEN l.votes = 0
        THEN 0
    ELSE
        round(c.candidate_votes::DECIMAL / l.votes * 100, 1)
    END as perc_to_list_votes

FROM list_results l
LEFT JOIN candidate_results c ON l.id = c.list_id
LEFT JOIN agg_election_results ar ON l.election_id = ar.election_id
ORDER BY
    l.votes DESC,
    c.candidate_votes DESC

