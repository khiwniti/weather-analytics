// Utility functions for transforming weather data
export function kelvinToCelsius(kelvin) {
  return kelvin - 273.15;
}

export function kelvinToFahrenheit(kelvin) {
  return (kelvin - 273.15) * 9/5 + 32;
}

export function metersPerSecondToKnots(mps) {
  return mps * 1.94384;
}

export function metersPerSecondToMph(mps) {
  return mps * 2.23694;
}

export function hpaToInhg(hpa) {
  return hpa * 0.02953;
}