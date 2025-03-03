import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter } from "expo-router";

export default function Header() {
  const router = useRouter()
  return (
    <View style={styles.header}>
      <Text style={styles.title}>Yeslove!</Text>
      <TouchableOpacity style={styles.button} onPress={() => router.replace("/")}>
        <Text style={styles.buttonText}>Log out</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    width: '100%',
    height: 60,
    backgroundColor: '#fff', 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingLeft: 20, 
    paddingTop: 5,
    marginTop: 0,
    justifyContent: 'space-between', 
  },
  title: {
    color: '#007bff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  profile: {
    marginRight: 30,
  },
  button: {
    borderRadius: 20,
    backgroundColor: "#2d5be3",
    paddingVertical: 10,
    paddingHorizontal: 10,
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
  }
});


