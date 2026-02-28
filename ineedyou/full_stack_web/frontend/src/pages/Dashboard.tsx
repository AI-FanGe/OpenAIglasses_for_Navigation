import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Box, Typography, Grid, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import axios from 'axios';

interface Device {
  id: number;
  name: string;
  device_id: string;
  is_active: boolean;
  last_seen: string;
}

interface Log {
  id: number;
  timestamp: string;
  level: string;
  message: string;
}

export default function Dashboard() {
  const { user, isAdmin, logout } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);

  useEffect(() => {
    fetchDevices();
    fetchLogs();
  }, []);

  const fetchDevices = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/devices/');
      setDevices(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/logs/');
      setLogs(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 4 }}>
        <Typography variant="h4">
          {isAdmin ? 'Admin Dashboard' : `Welcome, ${user?.username}`}
        </Typography>
        <Button variant="outlined" color="error" onClick={logout}>Logout</Button>
      </Box>

      <Grid container spacing={4}>
        <Grid item xs={12} md={6}>
          <Typography variant="h5" gutterBottom>Devices</Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Seen</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {devices.map((device) => (
                  <TableRow key={device.id}>
                    <TableCell>{device.name}</TableCell>
                    <TableCell>{device.device_id}</TableCell>
                    <TableCell>{device.is_active ? 'Active' : 'Inactive'}</TableCell>
                    <TableCell>{new Date(device.last_seen).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>

        <Grid item xs={12} md={6}>
          <Typography variant="h5" gutterBottom>Recent Logs</Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Level</TableCell>
                  <TableCell>Message</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.slice(0, 10).map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{new Date(log.timestamp).toLocaleTimeString()}</TableCell>
                    <TableCell>{log.level}</TableCell>
                    <TableCell>{log.message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
      </Grid>
    </Box>
  );
}
