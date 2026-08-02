-- VIAIOS Knowledge Graph Seed Data
-- Run: docker exec -i viaios-postgres psql -U viaios -d viaios < seed-knowledge-graph.cypher
-- Or via AGE: SELECT * FROM cypher('viaios', $$ ... $$) AS (v agtype);

-- Create entities
CREATE (:Person {id: 'P001', name: 'Person-A', type: 'suspect', description: 'Male, black jacket, 175cm'});
CREATE (:Person {id: 'P002', name: 'Person-B', type: 'witness', description: 'Female, white coat, 162cm'});
CREATE (:Person {id: 'P003', name: 'Person-C', type: 'suspect', description: 'Male, blue shirt, 180cm'});

CREATE (:Vehicle {id: 'V001', plate: '京A12345', type: 'car', color: 'black', brand: 'Audi'});
CREATE (:Vehicle {id: 'V002', plate: '京B67890', type: 'truck', color: 'white', brand: 'Dongfeng'});
CREATE (:Vehicle {id: 'V003', plate: '京C11111', type: 'motorcycle', color: 'red', brand: 'Honda'});

CREATE (:Camera {id: 'C001', name: 'Gate-A-Camera', location: 'Gate A', zone: 'entrance'});
CREATE (:Camera {id: 'C002', name: 'Gate-B-Camera', location: 'Gate B', zone: 'entrance'});
CREATE (:Camera {id: 'C003', name: 'Parking-Camera', location: 'Parking Lot', zone: 'parking'});
CREATE (:Camera {id: 'C004', name: 'Lobby-Camera', location: 'Main Lobby', zone: 'indoor'});

CREATE (:Location {id: 'L001', name: 'Gate A', type: 'entrance', latitude: 31.2304, longitude: 121.4737});
CREATE (:Location {id: 'L002', name: 'Gate B', type: 'entrance', latitude: 31.2310, longitude: 121.4745});
CREATE (:Location {id: 'L003', name: 'Parking Lot', type: 'parking', latitude: 31.2298, longitude: 121.4730});

CREATE (:Case {id: 'CASE001', title: 'Gate A Intrusion', status: 'open', severity: 'HIGH'});
CREATE (:Case {id: 'CASE002', title: 'Vehicle Theft', status: 'open', severity: 'CRITICAL'});

-- Create relationships
-- P001 appeared at cameras
MATCH (p:Person {id: 'P001'}), (c:Camera {id: 'C001'})
CREATE (p)-[:APPEARED_AT {timestamp: '2026-08-02T20:00:00Z', confidence: 0.95}]->(c);
MATCH (p:Person {id: 'P001'}), (c:Camera {id: 'C003'})
CREATE (p)-[:APPEARED_AT {timestamp: '2026-08-02T20:15:00Z', confidence: 0.88}]->(c);

-- P002 appeared at cameras
MATCH (p:Person {id: 'P002'}), (c:Camera {id: 'C002'})
CREATE (p)-[:APPEARED_AT {timestamp: '2026-08-02T20:05:00Z', confidence: 0.92}]->(p);

-- P003 appeared at cameras
MATCH (p:Person {id: 'P003'}), (c:Camera {id: 'C001'})
CREATE (p)-[:APPEARED_AT {timestamp: '2026-08-02T19:50:00Z', confidence: 0.87}]->(p);
MATCH (p:Person {id: 'P003'}), (c:Camera {id: 'C004'})
CREATE (p)-[:APPEARED_AT {timestamp: '2026-08-02T20:10:00Z', confidence: 0.91}]->(p);

-- Vehicles driven by persons
MATCH (p:Person {id: 'P001'}), (v:Vehicle {id: 'V001'})
CREATE (p)-[:DRIVES]->(v);
MATCH (p:Person {id: 'P003'}), (v:Vehicle {id: 'V002'})
CREATE (p)-[:DRIVES]->(v);

-- Persons met each other
MATCH (a:Person {id: 'P001'}), (b:Person {id: 'P003'})
CREATE (a)-[:MET {location: 'Gate A', timestamp: '2026-08-02T20:00:00Z'}]->(b);

-- Persons visited locations
MATCH (p:Person {id: 'P001'}), (l:Location {id: 'L001'})
CREATE (p)-[:VISITED {timestamp: '2026-08-02T20:00:00Z'}]->(l);
MATCH (p:Person {id: 'P001'}), (l:Location {id: 'L003'})
CREATE (p)-[:VISITED {timestamp: '2026-08-02T20:15:00Z'}]->(l);
MATCH (p:Person {id: 'P002'}), (l:Location {id: 'L002'})
CREATE (p)-[:VISITED {timestamp: '2026-08-02T20:05:00Z'}]->(l);

-- Cameras at locations
MATCH (c:Camera {id: 'C001'}), (l:Location {id: 'L001'})
CREATE (c)-[:LOCATED_AT]->(l);
MATCH (c:Camera {id: 'C002'}), (l:Location {id: 'L002'})
CREATE (c)-[:LOCATED_AT]->(l);
MATCH (c:Camera {id: 'C003'}), (l:Location {id: 'L003'})
CREATE (c)-[:LOCATED_AT]->(l);

-- Cases contain evidence
MATCH (c:Case {id: 'CASE001'}), (p:Person {id: 'P001'})
CREATE (c)-[:INVOLVES {role: 'suspect'}]->(p);
MATCH (c:Case {id: 'CASE001'}), (p:Person {id: 'P003'})
CREATE (c)-[:INVOLVES {role: 'suspect'}]->(p);
MATCH (c:Case {id: 'CASE002'}), (v:Vehicle {id: 'V001'})
CREATE (c)-[:INVOLVES {role: 'stolen_vehicle'}]->(v);
