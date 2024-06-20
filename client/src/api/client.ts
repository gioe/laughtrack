import axios, { AxiosResponse, AxiosRequestConfig, RawAxiosRequestHeaders } from 'axios';

const config: AxiosRequestConfig = {
  headers: {
    'Accept': 'application/json',
  } as RawAxiosRequestHeaders,
  baseURL: '/',
};

export default axios.create(config);