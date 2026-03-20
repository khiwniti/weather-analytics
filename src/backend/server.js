const express = require('express');
const app = express();
const port = process.env.PORT || 3001;

// Middleware
app.use(express.json());

// CORS configuration
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

// Root endpoint
app.get('/', (req, res) => {
  res.send('AI Weather Analytics API is running!');
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Get latest weather data for all sources
app.get('/api/weather/latest', (req, res) => {
  try {
    // TODO: Query actual processed Zarr data from /tmp or S3
    // For now, return sample data structure
    const data = {
      timestamp: new Date().toISOString(),
      sources: {
        gfs: {
          cycle: '12Z',
          valid_time: new Date().toISOString(),
          status: 'available',
          files_processed: 385,
        },
        hrrr: {
          cycle: new Date().getUTCHours() + 'Z',
          valid_time: new Date().toISOString(),
          status: 'available',
          files_processed: 19,
        },
        goes: {
          latest_image: new Date().toISOString(),
          status: 'available',
        },
        nexrad: {
          latest_scan: new Date().toISOString(),
          status: 'available',
        },
      },
    };
    res.json(data);
  } catch (error) {
    console.error('Error fetching latest weather data:', error);
    res.status(500).json({ error: 'Failed to fetch weather data' });
  }
});

// Get forecast for specific location
app.get('/api/weather/forecast/:location', (req, res) => {
  try {
    const { location } = req.params;
    const { lat, lon } = req.query;

    // Validate coordinates
    if (!lat || !lon) {
      return res.status(400).json({
        error: 'Missing required query parameters: lat, lon'
      });
    }

    const latitude = parseFloat(lat);
    const longitude = parseFloat(lon);

    if (isNaN(latitude) || isNaN(longitude)) {
      return res.status(400).json({
        error: 'Invalid coordinates: lat and lon must be numbers'
      });
    }

    if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      return res.status(400).json({
        error: 'Coordinates out of range: lat [-90,90], lon [-180,180]'
      });
    }

    // TODO: Query actual GFS/HRRR data for this location
    // For now, return sample forecast structure
    const forecast = {
      location: {
        name: location,
        lat: latitude,
        lon: longitude,
      },
      current: {
        temperature: 72,
        temperature_unit: 'F',
        humidity: 65,
        wind_speed: 10,
        wind_direction: 180,
        conditions: 'Partly Cloudy',
        timestamp: new Date().toISOString(),
      },
      hourly: Array.from({ length: 24 }, (_, i) => ({
        hour: i,
        temperature: 72 - Math.floor(Math.random() * 20),
        precipitation_probability: Math.floor(Math.random() * 100),
        wind_speed: 5 + Math.floor(Math.random() * 15),
      })),
      daily: Array.from({ length: 7 }, (_, i) => ({
        day: i,
        high: 75 + Math.floor(Math.random() * 15),
        low: 55 + Math.floor(Math.random() * 15),
        precipitation_probability: Math.floor(Math.random() * 100),
        conditions: ['Sunny', 'Cloudy', 'Rainy', 'Partly Cloudy'][Math.floor(Math.random() * 4)],
      })),
    };

    res.json(forecast);
  } catch (error) {
    console.error('Error fetching forecast:', error);
    res.status(500).json({ error: 'Failed to fetch forecast data' });
  }
});

// Get radar data for specific region
app.get('/api/weather/radar/:region', (req, res) => {
  try {
    const { region } = req.params;
    const { bbox } = req.query; // Format: "minLon,minLat,maxLon,maxLat"

    if (!bbox) {
      return res.status(400).json({
        error: 'Missing required query parameter: bbox (format: minLon,minLat,maxLon,maxLat)'
      });
    }

    const coords = bbox.split(',').map(parseFloat);
    if (coords.length !== 4 || coords.some(isNaN)) {
      return res.status(400).json({
        error: 'Invalid bbox format. Expected: minLon,minLat,maxLon,maxLat'
      });
    }

    // TODO: Query actual NEXRAD radar data for this region
    // For now, return sample radar data structure
    const radarData = {
      region: region,
      bbox: {
        minLon: coords[0],
        minLat: coords[1],
        maxLon: coords[2],
        maxLat: coords[3],
      },
      timestamp: new Date().toISOString(),
      data_url: `/data/radar/${region}/latest.zarr`, // Placeholder
      reflectivity: {
        min: 0,
        max: 75,
        unit: 'dBZ',
      },
      status: 'available',
    };

    res.json(radarData);
  } catch (error) {
    console.error('Error fetching radar data:', error);
    res.status(500).json({ error: 'Failed to fetch radar data' });
  }
});

// Get available data sources
app.get('/api/sources', (req, res) => {
  res.json({
    sources: [
      {
        id: 'gfs',
        name: 'GFS (Global Forecast System)',
        type: 'nwp',
        resolution: '0.25°',
        coverage: 'Global',
        update_frequency: '6 hours',
      },
      {
        id: 'hrrr',
        name: 'HRRR (High-Resolution Rapid Refresh)',
        type: 'nwp',
        resolution: '3 km',
        coverage: 'CONUS',
        update_frequency: '1 hour',
      },
      {
        id: 'goes',
        name: 'GOES-16/17 Satellite',
        type: 'satellite',
        resolution: '0.5-2 km',
        coverage: 'Western Hemisphere',
        update_frequency: '5-15 minutes',
      },
      {
        id: 'nexrad',
        name: 'NEXRAD Radar',
        type: 'radar',
        resolution: '250 m - 1 km',
        coverage: 'CONUS',
        update_frequency: '5 minutes',
      },
      {
        id: 'asos',
        name: 'ASOS (Automated Surface Observing System)',
        type: 'ground',
        resolution: 'Point observations',
        coverage: 'US airports',
        update_frequency: 'Hourly',
      },
    ],
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

app.listen(port, () => {
  console.log(`Backend server running on port ${port}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`Available endpoints:`);
  console.log(`  GET  /api/health`);
  console.log(`  GET  /api/weather/latest`);
  console.log(`  GET  /api/weather/forecast/:location?lat=&lon=`);
  console.log(`  GET  /api/weather/radar/:region?bbox=`);
  console.log(`  GET  /api/sources`);
});

module.exports = app;