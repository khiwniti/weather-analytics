import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Box,
  Chip,
} from '@mui/material';
import {
  WbSunny,
  Cloud,
  Opacity,
  Air,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import axios from 'axios';
import Layout from '../components/Layout';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001';

interface WeatherSource {
  cycle?: string;
  valid_time?: string;
  latest_image?: string;
  latest_scan?: string;
  status: string;
  files_processed?: number;
}

interface LatestWeather {
  timestamp: string;
  sources: {
    gfs: WeatherSource;
    hrrr: WeatherSource;
    goes: WeatherSource;
    nexrad: WeatherSource;
  };
}

interface ForecastData {
  location: {
    name: string;
    lat: number;
    lon: number;
  };
  current: {
    temperature: number;
    temperature_unit: string;
    humidity: number;
    wind_speed: number;
    wind_direction: number;
    conditions: string;
    timestamp: string;
  };
  hourly: Array<{
    hour: number;
    temperature: number;
    precipitation_probability: number;
    wind_speed: number;
  }>;
  daily: Array<{
    day: number;
    high: number;
    low: number;
    precipitation_probability: number;
    conditions: string;
  }>;
}

const PublicView: React.FC = () => {
  const [latestData, setLatestData] = useState<LatestWeather | null>(null);
  const [forecast, setForecast] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Default location (San Francisco)
  const defaultLat = 37.7749;
  const defaultLon = -122.4194;
  const defaultLocation = 'San Francisco, CA';

  useEffect(() => {
    fetchWeatherData();
  }, []);

  const fetchWeatherData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch latest data from all sources
      const latestResponse = await axios.get<LatestWeather>(
        `${API_BASE_URL}/api/weather/latest`
      );
      setLatestData(latestResponse.data);

      // Fetch forecast for default location
      const forecastResponse = await axios.get<ForecastData>(
        `${API_BASE_URL}/api/weather/forecast/${defaultLocation}`,
        {
          params: {
            lat: defaultLat,
            lon: defaultLon,
          },
        }
      );
      setForecast(forecastResponse.data);
    } catch (err) {
      console.error('Error fetching weather data:', err);
      setError('Failed to load weather data. Please ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    return status === 'available' ? 'success' : 'error';
  };

  const getConditionIcon = (conditions: string) => {
    if (conditions.toLowerCase().includes('sunny')) return <WbSunny />;
    if (conditions.toLowerCase().includes('cloud')) return <Cloud />;
    if (conditions.toLowerCase().includes('rain')) return <Opacity />;
    return <WbSunny />;
  };

  if (loading) {
    return (
      <Layout>
        <Container maxWidth="lg" sx={{ py: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <CircularProgress />
        </Container>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Alert severity="error">{error}</Alert>
        </Container>
      </Layout>
    );
  }

  return (
    <Layout>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h4" align="center" gutterBottom>
          Public Weather Dashboard
        </Typography>
        <Typography variant="subtitle1" align="center" color="text.secondary" gutterBottom>
          Real-time weather data from multiple sources
        </Typography>

        {/* Data Source Status */}
        <Box sx={{ my: 4 }}>
          <Typography variant="h6" gutterBottom>
            Data Source Status
          </Typography>
          <Grid container spacing={2}>
            {latestData && Object.entries(latestData.sources).map(([key, source]) => (
              <Grid item xs={12} sm={6} md={3} key={key}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      {key.toUpperCase()}
                    </Typography>
                    <Chip
                      label={source.status}
                      color={getStatusColor(source.status)}
                      size="small"
                    />
                    {source.cycle && (
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        Cycle: {source.cycle}
                      </Typography>
                    )}
                    {source.files_processed && (
                      <Typography variant="body2">
                        Files: {source.files_processed}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>

        {/* Current Weather */}
        {forecast && (
          <>
            <Box sx={{ my: 4 }}>
              <Typography variant="h6" gutterBottom>
                Current Conditions - {forecast.location.name}
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        {getConditionIcon(forecast.current.conditions)}
                        <Typography variant="h3" sx={{ ml: 2 }}>
                          {forecast.current.temperature}°{forecast.current.temperature_unit}
                        </Typography>
                      </Box>
                      <Typography variant="h6" gutterBottom>
                        {forecast.current.conditions}
                      </Typography>
                      <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={6}>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Opacity fontSize="small" sx={{ mr: 1 }} />
                            <Typography variant="body2">
                              Humidity: {forecast.current.humidity}%
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={6}>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Air fontSize="small" sx={{ mr: 1 }} />
                            <Typography variant="body2">
                              Wind: {forecast.current.wind_speed} mph
                            </Typography>
                          </Box>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>

                {/* 7-Day Forecast */}
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        7-Day Forecast
                      </Typography>
                      {forecast.daily.map((day) => (
                        <Box
                          key={day.day}
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            py: 1,
                            borderBottom: day.day < 6 ? '1px solid #eee' : 'none',
                          }}
                        >
                          <Typography variant="body2">
                            Day {day.day + 1}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {getConditionIcon(day.conditions)}
                            <Typography variant="body2" sx={{ mx: 1 }}>
                              {day.conditions}
                            </Typography>
                          </Box>
                          <Typography variant="body2">
                            {day.high}° / {day.low}°
                          </Typography>
                          <Typography variant="body2" color="primary">
                            {day.precipitation_probability}%
                          </Typography>
                        </Box>
                      ))}
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>

            {/* Hourly Temperature Chart */}
            <Box sx={{ my: 4 }}>
              <Typography variant="h6" gutterBottom>
                24-Hour Temperature Forecast
              </Typography>
              <Card>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={forecast.hourly}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="hour"
                        label={{ value: 'Hour', position: 'insideBottom', offset: -5 }}
                      />
                      <YAxis
                        label={{ value: 'Temperature (°F)', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="temperature"
                        stroke="#8884d8"
                        name="Temperature"
                        strokeWidth={2}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Box>

            {/* Precipitation Probability Chart */}
            <Box sx={{ my: 4 }}>
              <Typography variant="h6" gutterBottom>
                24-Hour Precipitation Probability
              </Typography>
              <Card>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={forecast.hourly}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="hour"
                        label={{ value: 'Hour', position: 'insideBottom', offset: -5 }}
                      />
                      <YAxis
                        label={{ value: 'Probability (%)', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="precipitation_probability"
                        stroke="#82ca9d"
                        name="Precipitation %"
                        strokeWidth={2}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Box>
          </>
        )}

        <Box sx={{ my: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Data updated: {latestData?.timestamp ? new Date(latestData.timestamp).toLocaleString() : 'N/A'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Location can be customized via search (coming soon)
          </Typography>
        </Box>
      </Container>
    </Layout>
  );
};

export default PublicView;
