import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native'
import React, { useState } from 'react';
import { useRouter } from "expo-router";
import axios from 'axios';
import {ApiApiFactory, ApiApi} from "../generated-api/api";


const Login = () => {
const router = useRouter();
const [password, setPassword] = useState("");
const [username, setUsername] = useState("")

const handleLogin = () => {
  testLogin(username, password)
}

const handlePasswordChange = (input) => {
  setPassword(input)
}

const handleUsernameChange = (input) => {
  setUsername(input)
}

const testLogin = (username, password) => {
  realmName = "YesLove_Auth";

  ApiApiFactory({}, "http://localhost:5000").postLogin({password: password, username: username})
  .then((response) => {
    //TODO store access and refresh token in redux store
    router.replace("/(tabs)/home");  
  }).catch((error) => {
    console.error('Login failed:', error);
  });


  ApiApiFactory().getUserProfile()

};


  return (
    <View style={styles.container}>
      <Text style={styles.title}>Login</Text>

      <Text style={styles.label}>Username</Text>
      <TextInput onChangeText={handleUsernameChange} value={username} style={styles.input} placeholder="Enter username" />

      <Text style={styles.label}>Password</Text>
      <TextInput onChangeText={handlePasswordChange} value={password} style={styles.input} placeholder="Enter password" secureTextEntry={true} />
    
      <TouchableOpacity style={styles.button} onPress={handleLogin}>
        <Text style={styles.buttonText}>Login</Text>
      </TouchableOpacity>
    </View>
  )
}



const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
    width: 400,
    backgroundColor: "#f5f5f5",
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 20,
    color: "#333",
  },
  label: {
    alignSelf: 'flex-start',
    fontSize: 16,
    marginBottom: 5,
    color: '#666',
  },
  input: {
    width: '100%',
    height: 50,
    borderColor: '#ccc',
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 10,
    backgroundColor: '#fff',
    marginBottom: 15,
  },
  button: {
    backgroundColor: '#007bff',
    paddingVertical: 12,
    paddingHorizontal: 40,
    borderRadius: 8,
    marginTop: 10,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});


export default Login