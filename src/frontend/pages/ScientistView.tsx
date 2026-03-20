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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Tabs,
  Tab,
} from '@mui/material';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import axios from 'axios';
import Layout from '../components/Layout';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001';

interface DataSource {
  id: string;
  name: string;
  type: string;
  resolution: string;
  coverage: string;
  update_frequency: string;
}

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
    [key: string]: WeatherSource;
  };
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const ScientistView: React.FC = () => {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [latestData, setLatestData] = useState<LatestWeather | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [sourcesResponse, latestResponse] = await Promise.all([
        axios.get<{ sources: DataSource[] }>(`${API_BASE_URL}/api/sources`),
        axios.get<LatestWeather>(`${API_BASE_URL}/api/weather/latest`),
      ]);

      setSources(sourcesResponse.data.sources);
      setLatestData(latestResponse.data);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load data. Please ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const getStatusColor = (status: string) => {
    return status === 'available' ? 'success' : 'error';
  };

  // Mock performance data for demonstration
  const performanceData = [
    { name: 'GFS', download: 120, process: 45, upload: 30 },
    { name: 'HRRR', download: 60, process: 25, upload: 15 },
    { name: 'GOES', download: 90, process: 35, upload: 20 },
    { name: 'NEXRAD', download: 40, process: 15, upload: 10 },
  ];

  if (loading) {
    return (
      <Layout>
        <Container maxWidth="xl" sx={{ py: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <CircularProgress />
        </Container>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <Container maxWidth="xl" sx={{ py: 4 }}>
          <Alert severity="error">{error}</Alert>
        </Container>
      </Layout>
    );
  }

  return (
    <Layout>
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom>
          Scientist View - Advanced Weather Analytics
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          Technical data ingestion and processing metrics
        </Typography>

        <Box sx={{ borderBottom: 1, borderColor: 'divider', my: 3 }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Data Sources" />
            <Tab label="Ingestion Status" />
            <Tab label="Performance Metrics" />
          </Tabs>
        </Box>

        {/* Tab 1: Data Sources */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>
            Available Data Sources
          </Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Source ID</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Resolution</TableCell>
                  <TableCell>Coverage</TableCell>
                  <TableCell>Update Frequency</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sources.map((source) => (
                  <TableRow key={source.id}>
                    <TableCell>
                      <Chip label={source.id.toUpperCase()} size="small" />
                    </TableCell>
                    <TableCell>{source.name}</TableCell>
                    <TableCell>
                      <Chip label={source.type} variant="outlined" size="small" />
                    </TableCell>
                    <TableCell>{source.resolution}</TableCell>
                    <TableCell>{source.coverage}</TableCell>
                    <TableCell>{source.update_frequency}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Tab 2: Ingestion Status */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Real-Time Ingestion Status
          </Typography>
          <Grid container spacing={3}>
            {latestData && Object.entries(latestData.sources).map(([key, source]) => (
              <Grid item xs={12} md={6} key={key}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6">
                        {key.toUpperCase()}
                      </Typography>
                      <Chip
                        label={source.status}
                        color={getStatusColor(source.status)}
                      />
                    </Box>
                    <Grid container spacing={2}>
                      {source.cycle && (
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            Cycle
                          </Typography>
                          <Typography variant="body1" fontWeight="bold">
                            {source.cycle}
                          </Typography>
                        </Grid>
                      )}
                      {source.files_processed !== undefined && (
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            Files Processed
                          </Typography>
                          <Typography variant="body1" fontWeight="bold">
                            {source.files_processed}
                          </Typography>
                        </Grid>
                      )}
                      {source.valid_time && (
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary">
                            Valid Time
                          </Typography>
                          <Typography variant="body2">
                            {new Date(source.valid_time).toLocaleString()}
                          </Typography>
                        </Grid>
                      )}
                      {source.latest_image && (
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary">
                            Latest Image
                          </Typography>
                          <Typography variant="body2">
                            {new Date(source.latest_image).toLocaleString()}
                          </Typography>
                        </Grid>
                      )}
                      {source.latest_scan && (
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary">
                            Latest Scan
                          </Typography>
                          <Typography variant="body2">
                            {new Date(source.latest_scan).toLocaleString()}
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Box sx={{ mt: 3 }}>
            <Alert severity="info">
              Data last updated: {latestData?.timestamp ? new Date(latestData.timestamp).toLocaleString() : 'N/A'}
            </Alert>
          </Box>
        </TabPanel>

        {/* Tab 3: Performance Metrics */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Pipeline Performance Metrics
          </Typography>
          <Alert severity="info" sx={{ mb: 3 }}>
            Note: These are sample metrics. Real metrics will be collected from Celery task execution times.
          </Alert>

          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Average Processing Time by Stage (seconds)
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={performanceData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis label={{ value: 'Time (s)', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="download" fill="#8884d8" name="Download" />
                      <Bar dataKey="process" fill="#82ca9d" name="Process" />
                      <Bar dataKey="upload" fill="#ffc658" name="Upload" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    System Configuration
                  </Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableBody>
                        <TableRow>
                          <TableCell>GPU Acceleration</TableCell>
                          <TableCell>RAPIDS (cuDF, cuSpatial)</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Task Queue</TableCell>
                          <TableCell>Celery + Redis</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Storage Format</TableCell>
                          <TableCell>Zarr (cloud-native)</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>QC Pipeline</TableCell>
                          <TableCell>Temporal + Gap Filling</TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Quick Stats
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Active Sources
                      </Typography>
                      <Typography variant="h4">
                        {sources.length}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Files Processed Today
                      </Typography>
                      <Typography variant="h4">
                        {latestData ? Object.values(latestData.sources).reduce(
                          (sum, source) => sum + (source.files_processed || 0), 0
                        ) : 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Storage Backend
                      </Typography>
                      <Typography variant="h6">
                        {process.env.REACT_APP_S3_ENABLED === 'true' ? 'S3 + Local' : 'Local /tmp'}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Pipeline Status
                      </Typography>
                      <Chip label="Operational" color="success" />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        <Box sx={{ mt: 4, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Note:</strong> This is the advanced scientific interface. For public weather information, visit the{' '}
            <a href="/" style={{ color: '#1976d2' }}>Public Dashboard</a>.
          </Typography>
        </Box>
      </Container>
    </Layout>
  );
};

export default ScientistView;
