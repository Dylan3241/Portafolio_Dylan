import java.util.Scanner;

public class carrito_de_compra {

    public static void main(String[] args) {

        Scanner sc = new Scanner(System.in);

        double total = 0;
        boolean seguir = true;

        System.out.println("=== Carrito de compras ===");

        while (seguir) {
            System.out.println("\n1. Agregar producto");
            System.out.println("2. Ver total");
            System.out.println("3. Finalizar compra");
            System.out.print("Elije una opcion: ");

            int opcion = sc.nextInt();
            sc.nextLine(); // limpiar buffer después de leer número

            if (opcion == 1) {
                System.out.print("Ingrese el nombre del producto: ");
                String producto = sc.nextLine();
                System.out.print("Ingrese el precio del producto: $");
                double precio = sc.nextDouble();

                total = total + precio;

                System.out.println("✅ Producto agregado: " + producto + " ($" + precio + ")");
                System.out.println("Total parcial: $" + total);
            } else if (opcion == 2) {
                System.out.println("🛒 Total acumulado: $" + total);
            } else if (opcion == 3) {
                System.out.println("\n=== Compra finalizada ===");
                System.out.println("Total a pagar: $" + total);
                seguir = false;
            } else {
                System.out.println("⚠️ La opción ingresada es incorrecta. Inténtelo de nuevo.");
            }
        }

        sc.close();
    }
}
