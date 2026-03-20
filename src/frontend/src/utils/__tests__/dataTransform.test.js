// Manual test for data transformation utilities
const { kelvinToCelsius, kelvinToFahrenheit, metersPerSecondToKnots, metersPerSecondToMph, hpaToInhg } = require('../dataTransform');

console.log('Running data transformation tests...\n');

// Test Kelvin to Celsius conversion
console.log('Testing kelvinToCelsius:');
console.log('0K ->', kelvinToCelsius(0), '°C (expected: -273.15)');
console.log('273.15K ->', kelvinToCelsius(273.15), '°C (expected: 0)');
console.log('300K ->', kelvinToCelsius(300), '°C (expected: 26.85)');
console.log('373.15K ->', kelvinToCelsius(373.15), '°C (expected: 100)');

// Test Kelvin to Fahrenheit conversion
console.log('\nTesting kelvinToFahrenheit:');
console.log('0K ->', kelvinToFahrenheit(0), '°F (expected: -459.67)');
console.log('273.15K ->', kelvinToFahrenheit(273.15), '°F (expected: 32)');
console.log('300K ->', kelvinToFahrenheit(300), '°F (expected: 80.33)');
console.log('373.15K ->', kelvinToFahrenheit(373.15), '°F (expected: 212)');

// Test meters per second to knots conversion
console.log('\nTesting metersPerSecondToKnots:');
console.log('0 m/s ->', metersPerSecondToKnots(0), 'knots (expected: 0)');
console.log('1 m/s ->', metersPerSecondToKnots(1), 'knots (expected: 1.94384)');
console.log('10 m/s ->', metersPerSecondToKnots(10), 'knots (expected: 19.4384)');

// Test meters per second to mph conversion
console.log('\nTesting metersPerSecondToMph:');
console.log('0 m/s ->', metersPerSecondToMph(0), 'mph (expected: 0)');
console.log('1 m/s ->', metersPerSecondToMph(1), 'mph (expected: 2.23694)');
console.log('10 m/s ->', metersPerSecondToMph(10), 'mph (expected: 22.3694)');

// Test hPa to inHg conversion
console.log('\nTesting hpaToInhg:');
console.log('0 hPa ->', hpaToInhg(0), 'inHg (expected: 0)');
console.log('1013.25 hPa ->', hpaToInhg(1013.25), 'inHg (expected: 29.9213)');
console.log('500 hPa ->', hpaToInhg(500), 'inHg (expected: 14.7953)');

console.log('\n✅ All manual tests completed!');